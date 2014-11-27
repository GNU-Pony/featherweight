#!/usr/bin/env python3
'''
featherweight – A lightweight terminal news feed reader

Copyright © 2013, 2014  Mattias Andrée (maandree@member.fsf.org)

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


args = sys.argv[1:]
status = '--status' in args
update = '--update' in args
system = '--system' in args


if not os.path.exists(root):
    os.makedirs(root)


def flatten(feeds, rc = None):
    if rc is None:
        rc = []
        flatten(feeds, rc)
        return rc
    else:
        for feed in feeds:
            rc.append(feed)
            if 'inner' in feed:
                flatten(feed['inner'], rc)



feeds = None
with touch('%s/feeds' % root) as feeds_flock:
    flock(feeds_flock, False, _('Feed database is locked by another process, waiting...'))
    with open('%s/feeds' % root, 'rb') as file:
        feeds = file.read()
    unflock(feeds_flock)
    feeds = feeds.decode('utf-8', 'strict')
    feeds = [] if len(feeds) == 0 else eval(feeds)
    if update or status:
        group = None
        for arg in args:
            if not arg.startswith('-'):
                group = arg
                break
        if update:
            old = dict((feed['id'], feed['new']) for feed in flatten(feeds))
            for feed in feeds:
                update_feed(feed, group)
            flock(feeds_flock, True, _('Feed database is locked by another process, waiting...'))
            new = [(feed['id'], feed['new']) for feed in flatten(feeds)]
            with open('%s/feeds' % root, 'rb') as file:
                feeds = file.read()
            feeds = feeds.decode('utf-8', 'strict')
            feeds = [] if len(feeds) == 0 else eval(feeds)
            flat_feeds = dict((feed['id'], feed) for feed in flatten(feeds))
            for id, new_value in new:
                if id in flat_feeds.keys():
                    flat_feeds[id]['new'] += new_value - old[id]
            updated = repr(feeds)
            data = updated.encode('utf-8')
            status_data = ('%i\n' % Tree.count_new(feeds)).encode('utf-8')
            with open('%s/feeds' % root, 'wb') as file:
                file.write(data)
            with open('%s/status' % root, 'wb') as file:
                file.write(status_data)
            unflock(feeds_flock)
        if status:
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
            elif not os.access('%s/status' % root, os.F_OK):
                print('0')
            else:
                flock(feeds_flock, False)
                with open('%s/status' % root, 'rb') as file:
                    sys.stdout.buffer.write(file.read())
                sys.stdout.buffer.flush()
                unflock(feeds_flock)


if system:
    sys.exit(0)


old_stty = Popen('stty --save'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
old_stty = old_stty.decode('utf-8', 'strict')[:-1]
Popen('stty -icanon -echo'.split(' '), stdout = PIPE, stderr = PIPE).communicate()
print('\033[?1049h\033[?25l\033[?9h', end = '', flush = True)



def update_feeds(function):
    global terminated
    function(feeds)
    Tree.count_new(feeds)
    with touch('%s/feeds' % root) as feeds_flock:
        pid = flock_fork(feeds_flock)
        if pid == 0:
            return
        _feeds = None
        with open('%s/feeds' % root, 'rb') as file:
            _feeds = file.read()
            with open('%s/feeds.bak' % root, 'wb') as bakfile:
                bakfile.write(_feeds)
            _feeds = _feeds.decode('utf-8', 'strict')
        _feeds = [] if len(_feeds) == 0 else eval(_feeds)
        function(_feeds)
        status = Tree.count_new(_feeds)
        _feeds = repr(_feeds)
        try:
            with open('%s/feeds' % root, 'wb') as file:
                file.write(_feeds.encode('utf-8'))
            try:
                with open('%s/status' % root, 'wb') as file:
                    file.write(('%i\n' % status).encode('utf-8'))
            except:
                pass
        except Exception as err:
            Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
            print('\n\033[?9l\033[?25h\033[?1049l' if pid is None else '\n', end = '', flush = True)
            print('\033[01;31m%s\033[00m', _('Your %s was saved to %s.bak') % ('%s/feeds' % abbr(root), '%s/feeds' % abbr(root)))
            terminated = True
            if pid is None:
                raise err
        unflock_fork(feeds_flock, pid)


try:
    tree = Tree('My Feeds', feeds)
    while True:
        (action, node) = tree.interact()
        if action == 'quit':
            break
        elif action == 'edit':
            if node is not None:
                table = {'Title' : node['title'], 'Group' : node['group'], 'URL' : '' if node['url'] is None else node['url']}
                values = {}
                saved = False
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
                text_area = TextArea(['Title', 'Group', 'URL'], table)
                text_area.initialise(False)
                print('\033[?25h\033[?9l', end = '', flush = True)
                text_area.run(saver)
                print('\033[?9h\033[?25l', end = '', flush = True)
                text_area.close()
                gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
                gettext.textdomain('@PKGNAME@')
                if saved:
                    update_feeds(lambda t : update_node(t, None if node is None else node['id'], values))
                print('\033[H\033[2J', end = '', flush = True)
                tree.draw_force = True
        elif action == 'open':
            if (node is None) or ('url' not in node) or (node['url'] is None) or (node['url'] == ''):
                continue
            def update(new):
                tree.count += new
                update_feeds(lambda t : update_node_newness(t, node['id'], new))
            if open_feed(node, update):
                break
            tree.draw_force = True
        elif action == 'add':
            if (node is None) or ('url' not in node) or (node['url'] is None) or (node['url'] == ''):
                table = {'Title' : '', 'Group' : '', 'URL' : ''}
                values = {'id' : str(uuid.uuid4()), 'new' : 0}
                saved = False
                def saver():
                    global table, values, saved
                    if table['Title'] == '':
                        return False
                    values['title'] = table['Title']
                    values['group'] = table['Group']
                    values['url'] = None if table['URL'] == '' else table['URL']
                    saved = True
                    return True
                text_area = TextArea(['Title', 'Group', 'URL'], table)
                text_area.initialise(False)
                print('\033[?25h\033[?9l', end = '', flush = True)
                text_area.run(saver)
                print('\033[?9h\033[?25l', end = '', flush = True)
                text_area.close()
                gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
                gettext.textdomain('@PKGNAME@')
                if saved:
                    update_feeds(lambda t : insert_node(t, None if node is None else node['id'], values))
                print('\033[H\033[2J', end = '', flush = True)
                tree.draw_force = True
        elif action == 'delete':
            if node is not None:
                Popen(['stty', 'echo', 'icanon'], stdout = PIPE, stderr = PIPE).communicate()
                print('\033[H\033[2J\033[?25h\033[?9l%s' % (_('Are you sure you to delete %s?') % double_quote(node['title'])))
                print(_('Type %s, if you are sure.') % quote(_('yes')))
                delete = sys.stdin.readline().replace('\n', '') == _('yes')
                Popen(['stty', '-echo', '-icanon'], stdout = PIPE, stderr = PIPE).communicate()
                print('\033[?25l\033[?9h', end = '', flush = True)
                if delete:
                    node = node['id']
                    update_feeds(lambda t : remove_node(t, node))
                    tree.select_stack.pop()
                print('\033[H\033[2J', end = '', flush = True)
                tree.draw_force = True
        elif action in ('up', 'down'):
            if node is None:
                continue
            parent = tree.select_stack[-2][0]
            id_p = None if parent is None else parent['id']
            parent = feeds if parent is None else parent['inner']
            nodei = tree.select_stack[-1][1]
            nodej = nodei + (-1 if action == 'up' else +1)
            if (nodei == 0) if action == 'up' else (nodei + 1 == len(parent)):
                continue
            id_i, id_j = parent[nodei]['id'], parent[nodej]['id']
            parent[nodei]['draw_line'] = -1
            parent[nodej]['draw_line'] = -1
            def save(t, id_t = None):
                if id_p == id_t:
                    i_is = [i for i in range(len(t)) if t[i]['id'] == id_i]
                    j_is = [i for i in range(len(t)) if t[i]['id'] == id_j]
                    if (i_is == [nodei]) and (j_is == [nodej]):
                        t[nodei], t[nodej] = t[nodej], t[nodei]
                    return True
                else:
                    for child in t:
                        if 'inner' in child:
                            if save(child['inner'], child['id']):
                                return True
                return False
            update_feeds(save)
            tree.select_stack[-1] = (parent[nodej], nodej)
        elif action == 'out':
            if len(tree.select_stack) < 3:
                continue
            parent = tree.select_stack[-2][0]
            id_p, id_n = parent['id'], node['id']
            def save(t, id_t = None, t_i = None, p = None):
                if id_p == id_t:
                    n_is = [i for i in range(len(t)) if t[i]['id'] == id_n]
                    if len(n_is) == 1:
                        n_i = n_is[0]
                        p.insert(t_i, t[n_i])
                        del t[n_i]
                        if len(t) == 0:
                            del p[t_i + 1]['inner']
                    return True
                else:
                    for i in range(len(t)):
                        child = t[i]
                        if 'inner' in child:
                            if save(child['inner'], child['id'], i, t):
                                return True
                return False
            update_feeds(save)
            tree.select_stack.pop()
            tree.select_stack[-1] = (node, tree.select_stack[-1][1])
            tree.draw_force = True
        elif action == 'in':
            if node is None:
                continue
            parent = tree.select_stack[-2][0]
            nodei = tree.select_stack[-1][1]
            id_p = None if parent is None else parent['id']
            parent = feeds if parent is None else parent['inner']
            if (nodei + 1 == len(parent)) or (parent[nodei + 1]['url'] is not None):
                continue
            id_n, id_m = node['id'], parent[nodei + 1]['id']
            def save(t, id_t = None):
                if id_p == id_t:
                    n_is = [i for i in range(len(t)) if t[i]['id'] == id_n]
                    m_is = [i for i in range(len(t)) if t[i]['id'] == id_m]
                    if (len(n_is) != 1) or (m_is != [n_is[0] + 1]):
                        return True
                    n_i, new_parent = n_is[0], t[m_is[0]]
                    if new_parent['url'] is not None:
                        return True
                    if 'inner' not in new_parent:
                        new_parent['inner'] = []
                    new_parent['inner'].insert(0, t[n_i])
                    del t[n_i]
                    return True
                else:
                    for i in range(len(t)):
                        child = t[i]
                        if 'inner' in child:
                            if save(child['inner'], child['id']):
                                return True
                return False
            update_feeds(save)
            tree.select_stack.pop()
            tree.select_stack.append((parent[nodei], nodei))
            tree.select_stack.append((parent[nodei]['inner'][0], 0))
            tree.draw_force = True
            node['draw_line'] = -1
        elif action in ('read', 'unread'):
            pass # we do not have entires, just feeds, nothing to read/unread
        elif action == 'back':
            pass # we are at the first page
        elif action in '012345678':
            if node is None:
                continue
            action = ... if action == '0' else (int(action) % 8)
            update_feeds(lambda t : update_node(t, node['id'], {'colour' : action}))
            node['draw_line'] = -1

except Exception as err:
    raise err
    pass
finally:
    if not terminated:
        Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
        print('\n\033[?9l\033[?25h\033[?1049l', end = '', flush = True)
