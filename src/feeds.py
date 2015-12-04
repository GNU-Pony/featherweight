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
from subprocess import Popen, PIPE

from pytagomacs.editor import *

from common import *
from common import _
from flocker import *
from trees import *

### Feed page. ###



MONTHS = { 1 : 'January',
           2 : 'February',
           3 : 'March',
           4 : 'April',
           5 : 'May',
           6 : 'June',
           7 : 'July',
           8 : 'August',
           9 : 'September',
          10 : 'October',
          11 : 'November',
          12 : 'December'}
'''
:dict<int, str>  Month number to month name map. Used to print the
                 month name in full in month-nodes, and abbreviated
                 in the date-nodes.
'''



def load_feed(id):
    '''
    Load the feeds
    
    @param   id:str                                    The ID of the feed
    @return  :(entries:itr<dict<str, int|str|↑>>,      Feed entries
               years:dict<str|int, int|str|↑|itr<↑>>,  Mapping for dates to branches in `entries`,
                                                       `years[2014][11][25]['inner']` lists all feeds entries
                                                       for 2014-(11)Nov-25.
               have:set<str>,                          A set of all ID:s of the leaves in `entries`
               unread:set<str>)                        A set of all ID:s of the read leaves in `entries`
    '''
    next_id = 0
    entries = []
    years = {}
    have, unread = set(), set()
    with touch('%s/%s' % (root, id)) as feed_flock:
        flock(feed_flock, False, _('The feed is locked by another process, waiting...'))
        feed_info, feed_data = None, None
        if os.access('%s/%s' % (root, id), os.F_OK):
            with open('%s/%s' % (root, id), 'rb') as file:
                feed_info = file.read()
            if os.access('%s/%s-content' % (root, id), os.F_OK):
                with open('%s/%s-content' % (root, id), 'rb') as file:
                    feed_data = file.read()
            unflock(feed_flock)
        
        feed_info = feed_info.decode('utf-8', 'strict')
        feed_info = eval(feed_info) if len(feed_info) > 0 else {}
        have   = set() if 'have'   not in feed_info else feed_info['have']
        unread = set() if 'unread' not in feed_info else feed_info['unread']
        
        if feed_data is not None:
            feed_data = eval(feed_data.decode('utf-8', 'strict'))
            for entry in feed_data:
                entry['new'] = 1 if entry['guid'] in unread else 0
                pubdate = entry['pubdate']
                entry['id'] = entry['guid']
                entry['realtitle'] = entry['title']
                title = entry['title'].split('\n')[0]
                entry['title'] = '(%02i:%02i:%02i) %s' % (pubdate[3], pubdate[4], pubdate[5], title)
                entry['time'] = (pubdate[3] * 60 + pubdate[4]) * 100 + pubdate[5]
                colour = entry['colour'] if 'colour' in entry else ...
                if pubdate[0] not in years:
                    year_entry = {}
                    years[pubdate[0]] = year_entry
                    entries.append(year_entry)
                    year_entry['year'] = pubdate[0]
                    year_entry['title'] = _('Year %i') % pubdate[0]
                    year_entry['inner'] = []
                    year_entry['id'] = next_id
                    next_id += 1
                months = years[pubdate[0]]
                if pubdate[1] not in months:
                    month_entry = {}
                    months[pubdate[1]] = month_entry
                    months['inner'].append(month_entry)
                    month_entry['year'] = pubdate[0]
                    month_entry['month'] = pubdate[1]
                    month_entry['title'] = MONTHS[pubdate[1]] if pubdate[1] in MONTHS else str(pubdate[1])
                    month_entry['inner'] = []
                    month_entry['id'] = next_id
                    next_id += 1
                days = months[pubdate[1]]
                if pubdate[2] not in days:
                    day_entry = {}
                    days[pubdate[2]] = day_entry
                    days['inner'].append(day_entry)
                    day_entry['year'] = pubdate[0]
                    day_entry['month'] = pubdate[1]
                    day_entry['day'] = pubdate[2]
                    title =  MONTHS[pubdate[1]][:3] if pubdate[1] in MONTHS else ''
                    title = '%03i-(%02i)%s-%02i' % (pubdate[0], pubdate[1], title, pubdate[2])
                    day_entry['title'] = title
                    day_entry['inner'] = []
                    day_entry['id'] = next_id
                    next_id += 1
                days[pubdate[2]]['inner'].append(entry)
                ancestors = [year_entry, month_entry, day_entry]
                if not colour == ...:
                    for ancestor in reversed(ancestors):
                        if 'colours' not in ancestor:
                            ancestor['colours'] = dict((c, 0) for c in list(range(8)))
                            ancestor['colours'][...] = len(ancestor['inner']) - 1
                        old_ancestor_colour = ancestor['colour'] if 'colour' in ancestor else ...
                        ancestor['colours'][colour] += 1
                        mode_c, mode_f = ..., 0
                        for c in range(8):
                            if mode_f < ancestor['colours'][c]:
                                mode_f = ancestor['colours'][c]
                                mode_c = c
                        if not old_ancestor_colour == mode_c:
                            if mode_c == ...:
                                del ancestor['colour']
                            else:
                                ancestor['colour'] = mode_c
                else:
                    for ancestor in ancestors:
                        if 'colours' in ancestor:
                            ancestor['colours'][...] += 1
    
    entries.sort(key = lambda x : -(x['year']))
    for year in entries:
        year['inner'].sort(key = lambda x : -(x['month']))
        for month in year['inner']:
            month['inner'].sort(key = lambda x : -(x['day']))
            for day in month['inner']:
                day['inner'].sort(key = lambda x : -(x['time']))
    
    return (entries, years, have, unread)



def update_entries(feed_id, function):
    '''
    Update the entries in a feed
    
    @param   feed_id:str                           The ID of the feed
    @param   function:(have:set, unread:set)→void  Function that modifies the feed information
    @return  :bool                                 Whether the feed was updated
    '''
    updated = False
    pathname = '%s/%s' % (root, feed_id)
    with touch(pathname) as feed_flock:
        flock(feed_flock, True)
        feed_info = make_backup(pathname)
        if feed_info is not None:
            feed_info = feed_info.decode('utf-8', 'strict')
            feed_info = eval(feed_info) if len(feed_info) > 0 else {}
            have   = set() if 'have'   not in feed_info else feed_info['have']
            unread = set() if 'unread' not in feed_info else feed_info['unread']
            updated_ = len(have) + len(unread)
            function(have, unread)
            save_file_or_die(pathname, True, lambda : repr(feed_info).encode('utf-8'))
            if not updated_ == len(have) + len(unread):
                updated = True
        unflock(feed_flock)
    return updated



def update_content_file(feed_id, function):
    '''
    Apply changes to a news feed content file
    
    @param  feed_in:str                              The ID of the feed
    @param  function:(itr<dict<str, int|str>>)→void  Function that modifies the content
    '''
    pathname = '%s/%s-content' % (root, feed_id)
    with touch(pathname) as feed_flock:
        pid = flock_fork(feed_flock)
        if pid == 0:
            return
        feed_content = make_backup(pathname)
        if feed_content is not None:
            feed_content = feed_content.decode('utf-8', 'strict')
            feed_content = eval(feed_content) if len(feed_content) > 0 else []
            function(feed_content)
            save_file_or_die(pathname, pid is None, lambda : repr(feed_content).encode('utf-8'))
        unflock_fork(feed_flock, pid)



def delete_entry_content(feed_id, guids):
    '''
    Delete entries from the content list of a feed
    
    @param  feed_in:str     The ID of the feed
    @param  guids:set<str>  The GUID:s of the messages to delete
    '''
    def fun(feed_content):
        i = len(feed_content)
        while i > 0:
            i -= 1
            if feed_content[i]['guid'] in guids:
                del feed_content[i]
    update_content_file(feed_id, fun)



def modify_entry(feed_id, updates):
    '''
    Modify a feed entry
    
    @param  feed_in:str                                       The ID of the feed
    @param  updates:dict<guid:str, values:dict<str, ¿?|...>>  Mapping from GUID:s, of the messages to update,
                                                              to mapping for keys to new values, `...` as a
                                                              value means that the key should be deleted
    '''
    def fun(feed_content):
        for content in feed_content:
            if content['guid'] in updates:
                values = updates[content['guid']]
                for key in values.keys():
                    if values[key] == ...:
                        del content[key]
                    else:
                        content[key] = values[key]
    update_content_file(feed_id, fun)



def open_feed(feed_node, callback):
    '''
    Inspect a feed
    
    @param   feed_node:dict<str, _|str>  The node in the feed tree we the feed we are inspecting
    @param   callback:(:int)→void        Notify the previous tree about an update, the parameter
                                         specifies how much should be added to ['new']
    @return  :bool                       Whether the entire program should exit
    '''
    id = feed_node['id']
    (entries, years, have, unread) = load_feed(id)
    tree = Tree(feed_node['title'], entries)
    
    def get_nodes(node, qualifier):
        nodes = []
        if (node is not None) and ('inner' not in node):
            if qualifier(node):
                nodes.append(node)
        else:
            inners = node['inner'] if node is not None else entries
            for inner in inners:
                nodes += get_nodes(inner, qualifier)
        return nodes
    
    def read_unread(mod, nodes):
        guids = [node['guid'] for node in nodes]
        updated = None
        def update(f, qualifer):
            [f(guid) for guid in guids if qualifer(guid)]
        if mod > 0:
            updated = update_entries(id, lambda _, unread : update(unread.add, lambda g : g not in unread))
            [unread.add(guid) for guid in guids if guid not in unread]
        elif mod < 0:
            updated = update_entries(id, lambda _, unread : update(unread.remove, lambda g : g in unread))
            [unread.remove(guid) for guid in guids if guid in unread]
        else:
            return
        tree.count += mod * len(guids)
        for node in nodes:
            pubdate = node['pubdate']
            ancestors = [years[pubdate[0]]]
            while len(ancestors) < 3:
                ancestors.append(ancestors[-1][pubdate[len(ancestors)]])
            ancestors.append(node)
            for node in ancestors:
                node['new'] += mod
                node['draw_line'] = -1
            tree.redraw_root = True
        if updated:
            callback(mod * len(guids))
    
    # Session.
    while True:
        # Get input command from user.
        (action, node) = tree.interact()
        # Exit.
        if action == 'quit':
            return True
        # Back to the first page.
        elif action == 'back':
            return False
        # Edit article.
        elif action == 'edit':
            if (node is not None) and ('inner' not in node):
                table = {'Title' : node['realtitle'].split('\n')[0]}
                values = {}
                saved = False
                def saver():
                    nonlocal table, saved, values
                    values['title'] = table['Title']
                    saved = True
                    return True
                text_area = TextArea(['Title'], table)
                text_area.initialise(False)
                print('\033[?25h\033[?9l', end = '', flush = True)
                text_area.run(saver)
                print('\033[?9h\033[?25l', end = '', flush = True)
                text_area.close()
                gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
                gettext.textdomain('@PKGNAME@')
                if saved:
                    node['realtitle'] = values['title']
                    pubdate = node['pubdate']
                    pubdate = '%02i:%02i:%02i' % (pubdate[3], pubdate[4], pubdate[5])
                    node['title'] = '(%s) %s' % (pubdate, values['title'])
                    modify_entry(id, {node['guid'] : values})
                print('\033[H\033[2J', end = '', flush = True)
                tree.draw_force = True
        # Open article.
        elif action == 'open':
            if (node is not None) and ('inner' not in node):
                description = ''
                if 'link' in node:
                    description += '%s<br><br>' % (_('Link: %s') % node['link'])
                if 'description' in node:
                    description += node['description']
                description = description.encode('utf-8')
                proc = ['html2text']
                if ('FEATHERWEIGHT_HTML' in os.environ) and (not os.environ['FEATHERWEIGHT_HTML'] == ''):
                    proc = ['sh', '-c', os.environ['FEATHERWEIGHT_HTML']]
                proc = Popen(proc, stdin = PIPE, stdout = PIPE, stderr = sys.stderr)
                description = proc.communicate(description)[0]
                pager = os.environ['PAGER'] if 'PAGER' in os.environ else None
                pager = None if pager == '' else pager
                if pager is None:
                    path = os.environ['PATH'] if 'PATH' in os.environ else None
                    if path is not None:
                        path = path.split(':')
                        for pg in ['less', 'more', 'most', 'pg']:
                            for p in path:
                                if os.access('%s/%s' % (p, pg), os.X_OK):
                                    pager = pg
                                    break
                            if pager is not None:
                                break
                if pager is not None:
                    print('\033[H\033[2J\033[?9l\033[?25h\033[?1049l', end = '', flush = True)
                    proc = Popen(['sh', '-c', pager], stdin = PIPE, stdout = sys.stdout, stderr = sys.stderr)
                    proc.communicate(description)
                    print('\033[?1049h\033[?25l\033[?9h\033[H\033[2J', end = '', flush = True)
                else:
                    print('\033[H\033[2J\033[?9l', end = '', flush = True)
                    sys.stdout.buffer.write(description)
                    sys.stdout.buffer.flush()
                    while sys.stdin.read(1)[0] != '\n':
                        pass
                    print('\033[?9h\033[H\033[2J', end = '', flush = True)
                tree.draw_force = True
        # Add node.
        elif action == 'add':
            # “Add”, add what?
            pass
        # Move node upward, downward, outward, or inward.
        elif action in ('up', 'down', 'out', 'in'):
            # Cannot reorder nodes, they are sorted.
            pass
        # Delete node.
        elif action == 'delete':
            if node is None:
                continue
            Popen(['stty', 'echo', 'icanon'], stdout = PIPE, stderr = PIPE).communicate()
            print('\033[H\033[2J\033[?25h\033[?9l%s' % (_('Are you sure you to delete %s?') % double_quote(node['title'])))
            print(_('Type %s, if you are sure.') % quote(_('yes')))
            delete = sys.stdin.readline().replace('\n', '') == _('yes')
            Popen(['stty', '-echo', '-icanon'], stdout = PIPE, stderr = PIPE).communicate()
            print('\033[?25l\033[?9h', end = '', flush = True)
            print('\033[H\033[2J', end = '', flush = True)
            tree.draw_force = True
            if not delete:
                continue
            read_unread(-1, get_nodes(node, lambda n : n['new'] == 1))
            guids = [n['guid'] for n in get_nodes(node, lambda _ : True)]
            delete_entry_content(id, set(guids))
            def delete_node(nodes, node_id):
                for i in range(len(nodes)):
                    if nodes[i]['id'] == node_id:
                        del nodes[i]
                        tree.select_stack.pop()
                        return True
                    elif 'inner' in nodes[i]:
                        if delete_node(nodes[i]['inner'], node_id):
                            if len(nodes[i]['inner']) == 0:
                                del nodes[i]
                                tree.select_stack.pop()
                            return True
                return False
            delete_node(entries, node['id'])
        # Mark node, and its children, as read.
        elif action == 'read':
            read_unread(-1, get_nodes(node, lambda n : n['new'] == 1))
        # Mark node, and its children, as unread.
        elif action == 'unread':
            read_unread(+1, get_nodes(node, lambda n : n['new'] == 0))
        # Colour node.
        elif action in '012345678':
            if (node is None) or ('inner' in node):
                # Cannot colour root, or branch directly.
                continue
            # Get desired and current colour.
            action = ... if action == '0' else (int(action) % 8)
            old_colour = node['colour'] if 'colour' in node else ...
            if action == old_colour:
                # Why continue if the colour will not change?
                continue
            #
            modify_entry(id, {node['guid'] : {'colour' : action}})
            if action == ...:
                del node['colour']
            else:
                node['colour'] = action
            node['draw_line'] = -1
            pubdate = node['pubdate']
            ancestors = [years[pubdate[0]]]
            while len(ancestors) < 3:
                ancestors.append(ancestors[-1][pubdate[len(ancestors)]])
            for ancestor in reversed(ancestors):
                if 'colours' not in ancestor:
                    ancestor['colours'] = dict((c, 0) for c in list(range(8)))
                    ancestor['colours'][...] = len(ancestor['inner'])
                old_ancestor_colour = ancestor['colour'] if 'colour' in ancestor else ...
                ancestor['colours'][old_colour] -= 1
                ancestor['colours'][action] += 1
                mode_c, mode_f = ..., 0
                for c in range(8):
                    if mode_f < ancestor['colours'][c]:
                        mode_f = ancestor['colours'][c]
                        mode_c = c
                if not old_ancestor_colour == mode_c:
                    if mode_c == ...:
                        del ancestor['colour']
                    else:
                        ancestor['colour'] = mode_c
                    ancestor['draw_line'] = -1

