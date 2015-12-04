#!/usr/bin/env python3
'''
featherweight – A lightweight terminal news feed reader

Copyright © 2013, 2014, 2015  Mattias Andrée (maandree@member.fsf.org)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import os
import sys
import uuid
from subprocess import Popen, PIPE

from pytagomacs.editor import *

from common import *
from common import _
from flocker import *
from trees import *
from updater import *
from feeds import *

### Prologue and feed tree page. ###



args = sys.argv[1:]
'''
:itr<str>  Command line arguments, excluding the name of the process.
'''


status = '--status' in args
'''
:bool  Print the number of unread news?
'''

update = '--update' in args
'''
:bool  Fetch the latest news?
'''

system = '--system' in args
'''
:bool  Do not open interactive session?
'''

repair = '--repair' in args
'''
:bool  Repair errors in the feed database?
'''


# Ensure the existance of the directory for data files.
if not os.path.exists(root):
    os.makedirs(root)



def flatten(feeds, rc = None):
    '''
    Return all list of all nodes
    
    @param   feeds:itr<dict<str, _|↑>>  List of trees
    @param   rc:list<dict<str, _|↑>>?   List to populate and return; for method internal use
    @return  :list<dict<str, _|↑>>      List of all nodes
    '''
    if rc is None:
        rc = []
        flatten(feeds, rc)
        return rc
    else:
        for feed in feeds:
            rc.append(feed)
            if 'inner' in feed:
                flatten(feed['inner'], rc)


def save_feeds_and_status(feeds, status):
    '''
    Save feed list file and new-article-count file
    
    @param  feeds:itr<dict<str, _|↑>>  The feeds
    @param  status:int                 The number of unread articles
    '''
    # Format data to store in files.
    feeds = repr(feeds).encode('utf-8')
    status = ('%i\n' % status).encode('utf-8')
    # Update the feed list file.
    with open('%s/feeds' % root, 'wb') as file:
        file.write(feeds)
    # Create a backup of it too.
    with open('%s/feeds.bak' % root, 'wb') as file:
        file.write(feeds)
    # Update file with new-article count.
    # This must be done only whilst the feed-list file is locked.
    with open('%s/status' % root, 'wb') as file:
        file.write(status)


# Load feeds, and possiblity do more with it.
feeds = None
with touch('%s/feeds' % root) as feeds_flock:
    # Read file, with a lock on it as short as possible.
    flock(feeds_flock, False, _('Feed database is locked by another process, waiting...'))
    with open('%s/feeds' % root, 'rb') as file:
        feeds = file.read()
    unflock(feeds_flock)
    # Decode and parse file.
    feeds = feeds.decode('utf-8', 'strict')
    feeds = [] if len(feeds) == 0 else eval(feeds)
    # --update, --repair, --status
    if update or repair or status:
        # Get affected group.
        group = None
        for arg in args:
            if not arg.startswith('-'):
                group = arg
                break
        ### --update (fetch new articles) ###
        if update:
            # Create map from ID to new-article count.
            old_counts = dict((feed['id'], feed['new']) for feed in flatten(feeds))
            # Fetch new articles.
            for feed in feeds:
                update_feed(feed, group)
            # Lock the feed-list file for writing.
            flock(feeds_flock, True, _('Feed database is locked by another process, waiting...'))
            # Create list of ID–new-article count-pairs, with new counts.
            new = [(feed['id'], feed['new']) for feed in flatten(feeds)]
            # Re-read feed list file to avoid race conditions with other processes.
            with open('%s/feeds' % root, 'rb') as file:
                feeds = file.read()
            feeds = feeds.decode('utf-8', 'strict')
            feeds = [] if len(feeds) == 0 else eval(feeds)
            # Increase new-article counts with how much we increased it would.
            # (Remember than another process may have updated it too.)
            flat_feeds = dict((feed['id'], feed) for feed in flatten(feeds))
            for id, new_value in new:
                if id in flat_feeds.keys():
                    flat_feeds[id]['new'] += new_value - old_counts[id]
            # Save updates.
            save_feeds_and_status(feeds, Tree.count_new(feeds))
            # We are done, unlock the file.
            unflock(feeds_flock)
        ### --repair (repair damages) ###
        if repair:
            # Lock the feed-list file for writing.
            flock(feeds_flock, True, _('Feed database is locked by another process, waiting...'))
            # Recount new articles and repair feeds.
            new_status = 0
            for feed in flatten(feeds):
                pathname = '%s/%s' % (root, feed['id'])
                # File does not exist? That just means that its too new.
                if not os.access(pathname, os.F_OK):
                    continue
                # Open feed channel file for reading.
                with open(pathname, 'rb') as file:
                    # Lock the feed file for reading, and read.
                    flock(file, False, _('The feed is locked by another process, waiting...'))
                    feed_info = file.read()
                    # Back up the file.
                    with open('%s.bak' % pathname, 'wb') as bakfile:
                        bakfile.write(feed_info)
                    # Decode and parse feed file.
                    feed_info = feed_info.decode('utf-8', 'strict')
                    feed_info = eval(feed_info) if len(feed_info) > 0 else {}
                    # Get 'have'-set and 'unread'-set.
                    have   = set() if 'have'   not in feed_info else feed_info['have']
                    unread = set() if 'unread' not in feed_info else feed_info['unread']
                    feed_info['have'] = have
                    feed_info['unread'] = unread
                    # unread ≔ unread ∖ ∁have.
                    for unread_entry in list(unread):
                        if unread_entry not in have:
                            del unread[unread_entry]
                    # Store correct new-article count, and increment grand total.
                    feed['new'] = len(unread)
                    new_status += len(unread)
                    # Save repaired feed file.
                    try:
                        feed_info = repr(feed_info).encode('utf-8')
                        with open(pathname, 'wb') as mewfile:
                            mewfile.write(feed_info)
                        unflock(file)
                    except Exception as err:
                        unflock(file)
                        pathname = abbr(root) + pathname[len(root):]
                        print('\033[01;31m%s\033[00m', _('Your %s was saved to %s.bak') % (pathname, pathname))
                        raise err
            # Save changes.
            save_feeds_and_status(feeds, new_status)
            # We are done, unlock the file.
            unflock(feeds_flock)
        ### --status (report new-article count) ###
        if status:
            # If a group is specified, count only in that group.
            if group is not None:
                def get_status(feeds, in_group):
                    global group
                    count = 0
                    for feed in feeds:
                        inside = in_group or (feed['group'] == group)
                        if 'inner' in feed:
                            count += get_status(feed['inner'], inside)
                        elif inside:
                            count += feed['new']
                    return count
                print(get_status(feeds, False))
            # Otherwise, use status file.
            elif not os.access('%s/status' % root, os.F_OK):
                # New-article count is zero if it does not exist.
                print('0')
            else:
                flock(feeds_flock, False)
                with open('%s/status' % root, 'rb') as file:
                    sys.stdout.buffer.write(file.read())
                sys.stdout.buffer.flush()
                unflock(feeds_flock)


# We are done, if no interactive session is wanted.
if system:
    sys.exit(0)


# Configure the terminal to clear restore itself when we exit,
# not display the text cursor, report mouse clicks events,
# not echo types keys, do use direct instead of buffered input.
old_stty = Popen('stty --save'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
old_stty = old_stty.decode('utf-8', 'strict')[:-1]
Popen('stty -icanon -echo'.split(' '), stdout = PIPE, stderr = PIPE).communicate()
print('\033[?1049h\033[?25l\033[?9h', end = '', flush = True)



def update_feeds(function):
    '''
    Make changes to the feeds and save them asynchronously (and a separate process)
    
    @param  function:(feeds:itr<dict<str, _|↑>>)→void  Function that modifies the feeds
    '''
    # Make changes.
    function(feeds)
    # Update new article counts.
    Tree.count_new(feeds)
    # Save changes.
    pathname = '%s/feeds' % root
    with touch(pathname) as feeds_flock:
        pid = flock_fork(feeds_flock)
        if pid == 0:
            return
        feeds_ = make_backup(pathname, False).decode('utf-8', 'strict')
        feeds_ = [] if len(feeds_) == 0 else eval(feeds_)
        function(feeds_)
        if save_file_or_die(pathname, pid is None, lambda : repr(feeds_).encode('utf-8')):
            try:
                status = Tree.count_new(feeds_)
                with open('%s/status' % root, 'wb') as file:
                    file.write(('%i\n' % status).encode('utf-8'))
            except:
                pass
        unflock_fork(feeds_flock, pid)


# Interactive session.
try:
    # Create tree of feed list.
    tree = Tree('My Feeds', feeds)
    # Session.
    while True:
        # Get input command from user.
        (action, node) = tree.interact()
        # Exit.
        if action == 'quit':
            break
        # Edit node.
        elif action == 'edit':
            if node is None:
                # Cannot edit root.
                continue
            table = {'Title' : node['title'], 'Group' : node['group'], 'URL' : '' if node['url'] is None else node['url']}
            values = {}
            saved = False
            # Callback-function, for the editor, used to retrieve the changes.
            def saver():
                global table, saved, values, node
                if table['Title'] == '':
                    return False
                if (not table['URL'] == '') and ('inner' in node):
                    if (node['inner'] is None) or (len(node['inner']) == 0):
                        values['inner'] = ...
                    else:
                        return False
                values['title'] = table['Title']
                values['group'] = table['Group']
                values['url'] = None if table['URL'] == '' else table['URL']
                saved = True
                return True
            # Open editor.
            text_area = TextArea(['Title', 'Group', 'URL'], table)
            text_area.initialise(False)
            print('\033[?25h\033[?9l', end = '', flush = True)
            text_area.run(saver)
            print('\033[?9h\033[?25l', end = '', flush = True)
            text_area.close()
            # Restore locale, if editor change it.
            gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
            gettext.textdomain('@PKGNAME@')
            # Any changes?
            if saved:
                # Apply them.
                update_feeds(lambda t : update_node(t, None if node is None else node['id'], values))
            # Redraw the screen, now that there is not editor open anymore.
            print('\033[H\033[2J', end = '', flush = True)
            tree.draw_force = True
        # Open feed.
        elif action == 'open':
            if (node is None) or ('url' not in node) or (node['url'] is None) or (node['url'] == ''):
                # Cannot open unless it is a feed, not groups and root.
                continue
            # When changes are made, we will save directy (rather than waiting
            # until we get back here) if they affect the feed list file.
            def update(new):
                tree.count += new
                update_feeds(lambda t : update_node_newness(t, node['id'], new))
            # Open the page for the feed.
            if open_feed(node, update):
                # This means that the user selected to quit rather than return.
                break
            # Redraw the screen, now that the feed's page is not on it anymore.
            tree.draw_force = True
        # Add new node.
        elif action == 'add':
            if (node is not None) and ('url' in node) and (node['url'] is not None) and not (node['url'] == ''):
                # Cannot add nodes inside news feeds.
                continue
            table = {'Title' : '', 'Group' : '', 'URL' : ''}
            values = {'id' : str(uuid.uuid4()), 'new' : 0}
            saved = False
            # Callback-function, for the editor, used to retrieve the written data.
            def saver():
                global table, values, saved
                if table['Title'] == '':
                    return False
                values['title'] = table['Title']
                values['group'] = table['Group']
                values['url'] = None if table['URL'] == '' else table['URL']
                saved = True
                return True
            # Open editor.
            text_area = TextArea(['Title', 'Group', 'URL'], table)
            text_area.initialise(False)
            print('\033[?25h\033[?9l', end = '', flush = True)
            text_area.run(saver)
            print('\033[?9h\033[?25l', end = '', flush = True)
            text_area.close()
            # Restore locale, if editor change it.
            gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
            gettext.textdomain('@PKGNAME@')
            # Did the user go through with it?
            if saved:
                # Add the node.
                update_feeds(lambda t : insert_node(t, None if node is None else node['id'], values))
            # Redraw the screen, now that there is not editor open anymore.
            print('\033[H\033[2J', end = '', flush = True)
            tree.draw_force = True
        # Delete node.
        elif action == 'delete':
            if node is None:
                # Cannot delete root, silly.
                continue
            # Confirm end-of-the-world-dangerous action.
            Popen(['stty', 'echo', 'icanon'], stdout = PIPE, stderr = PIPE).communicate()
            print('\033[H\033[2J\033[?25h\033[?9l%s' % (_('Are you sure you to delete %s?') % double_quote(node['title'])))
            print(_('Type %s, if you are sure.') % quote(_('yes')))
            delete = sys.stdin.readline().replace('\n', '') == _('yes')
            Popen(['stty', '-echo', '-icanon'], stdout = PIPE, stderr = PIPE).communicate()
            print('\033[?25l\033[?9h', end = '', flush = True)
            # Did the user really want this?
            if delete:
                # Delete the node.
                node = node['id']
                update_feeds(lambda t : remove_node(t, node))
                tree.select_stack.pop()
            #  Redraw the screen, now that there is no dialogue on it.
            print('\033[H\033[2J', end = '', flush = True)
            tree.draw_force = True
        # Move up or down.
        elif action in ('up', 'down'):
            if node is None:
                # Root is stationary.
                continue
            # Get parent node.
            parent = tree.select_stack[-2][0]
            id_p = None if parent is None else parent['id']
            parent = feeds if parent is None else parent['inner']
            # Get the position of the selected node and its adjacent.
            nodei = tree.select_stack[-1][1]
            nodej = nodei + (-1 if action == 'up' else +1)
            if (nodei == 0) if action == 'up' else (nodei + 1 == len(parent)):
                # Cannot move up if at beginning, or down if at end.
                continue
            id_i, id_j = parent[nodei]['id'], parent[nodej]['id']
            # We will have to redraw the swapped lines.
            parent[nodei]['draw_line'] = -1
            parent[nodej]['draw_line'] = -1
            # Function for moving the node.
            def save(t, id_t = None):
                # We need to search, because another process may have modified the tree.
                # Visiting the parent?
                if id_p == id_t:
                    # Find positions of the selected node and its adjacent.
                    i_is = [i for i in range(len(t)) if t[i]['id'] == id_i]
                    j_is = [i for i in range(len(t)) if t[i]['id'] == id_j]
                    if (i_is == [nodei]) and (j_is == [nodej]):
                        # Swap their positions.
                        t[nodei], t[nodej] = t[nodej], t[nodei]
                    return True
                # Visit children.
                else:
                    for child in t:
                        if 'inner' in child:
                            if save(child['inner'], child['id']):
                                return True
                # No luck.
                return False
            # Apply changes.
            update_feeds(save)
            # Update selection stack.
            tree.select_stack[-1] = (parent[nodej], nodej)
        # Move outward (that is left.)
        elif action == 'out':
            if len(tree.select_stack) < 3:
                # Root is stationary.                         (len(tree.select_stack) == 1)
                # Cannot move into root, need another parent. (len(tree.select_stack) == 2)
                continue
            # Whither?
            parent = tree.select_stack[-2][0]
            id_p = parent['id'],
            # Whence?
            id_n = node['id']
            # Function for moving the node.
            def save(t, id_t = None, t_i = None, p = None):
                # We need to search, because another process may have modified the tree.
                # Visiting the parent?
                if id_p == id_t:
                    # Find position of selected node.
                    n_is = [i for i in range(len(t)) if t[i]['id'] == id_n]
                    if len(n_is) == 1:
                        n_i = n_is[0]
                        # Move the node.
                        p.insert(t_i, t[n_i])
                        del t[n_i]
                        # Mark the parent as a leaf if it is empty.
                        if len(t) == 0:
                            del p[t_i + 1]['inner']
                    return True
                # Visit children.
                else:
                    for i in range(len(t)):
                        child = t[i]
                        if 'inner' in child:
                            if save(child['inner'], child['id'], i, t):
                                return True
                # No luck. What the fuck! (Probably, because of changes from another process.)
                return False
            # Apply changes.
            update_feeds(save)
            # Update selection stack.
            tree.select_stack.pop()
            tree.select_stack[-1] = (node, tree.select_stack[-1][1])
            # Force redraw.
            tree.draw_force = True
        # Move inward (that is right.)
        elif action == 'in':
            if node is None:
                # Root is stationary.
                continue
            # Get parent node.
            parent = tree.select_stack[-2][0]
            id_p = None if parent is None else parent['id']
            parent = feeds if parent is None else parent['inner']
            # Get selected node.
            nodei = tree.select_stack[-1][1]
            id_n = node['id']
            # Verify that there is a branch beneath the selected node.
            if (nodei + 1 == len(parent)) or (parent[nodei + 1]['url'] is not None):
                continue
            # Get the node beneath the select node, its parent-to-be.
            id_m = parent[nodei + 1]['id']
            # Function for moving the node.
            def save(t, id_t = None):
                # We need to search, because another process may have modified the tree.
                # Visiting the parent?
                if id_p == id_t:
                    # Find position of the select node, and the node beneath it.
                    n_is = [i for i in range(len(t)) if t[i]['id'] == id_n]
                    m_is = [i for i in range(len(t)) if t[i]['id'] == id_m]
                    if (len(n_is) != 1) or (m_is != [n_is[0] + 1]):
                        return True
                    n_i = n_is[0]
                    # Get new parent.
                    new_parent = t[m_is[0]]
                    if new_parent['url'] is not None:
                        return True
                    # Reparent.
                    if 'inner' not in new_parent:
                        new_parent['inner'] = []
                    new_parent['inner'].insert(0, t[n_i])
                    del t[n_i]
                    return True
                # Visit children.
                else:
                    for i in range(len(t)):
                        child = t[i]
                        if 'inner' in child:
                            if save(child['inner'], child['id']):
                                return True
                # No luck.
                return False
            # Apply changes.
            update_feeds(save)
            # Update selection stack.
            tree.select_stack.pop()
            tree.select_stack.append((parent[nodei], nodei))
            tree.select_stack.append((parent[nodei]['inner'][0], 0))
            # Force redraw.
            tree.draw_force = True
            node['draw_line'] = -1
        # Mark as read or not.
        elif action in ('read', 'unread'):
            # We do not have entires, just feeds, nothing to read/unread.
            # Implement feed-wide read/unread here is a bad idea.
            pass
        # To the previous page.
        elif action == 'back':
            # We are at the first page.
            pass
        # Colour node.
        elif action in '012345678':
            if node is None:
                continue
            action = ... if action == '0' else (int(action) % 8)
            update_feeds(lambda t : update_node(t, node['id'], {'colour' : action}))
            node['draw_line'] = -1

# Error?
except Exception as err:
    raise err
    pass
# Terminal not already restored? Restore it.
finally:
    if not terminated:
        Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
        print('\n\033[?9l\033[?25h\033[?1049l', end = '', flush = True)

