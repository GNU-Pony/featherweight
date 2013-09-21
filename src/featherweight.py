#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
featherweight – A lightweight terminal news feed reader

Copyright © 2013  Mattias Andrée (maandree@member.fsf.org)

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

import gettext
gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
gettext.textdomain('@PKGNAME@')
_ = gettext.gettext

from flocker import *
from trees import *
from updater import *
from editor import *


old_stty = Popen('stty --save'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
old_stty = old_stty.decode('utf-8', 'error')[:-1]

Popen('stty -icanon -echo'.split(' '), stdout = PIPE, stderr = PIPE).communicate()


args = sys.argv[1:]
update = '--update' in args
system = '--system' in args


islinux = ('TERM' in os.environ) and (os.environ['TERM'] == 'linux')
home = os.environ['HOME']

quote = (lambda x : "'%s'" % x) if islinux else (lambda x : '‘%s’' % x)
double_quote = (lambda x : '"%s"' % x) if islinux else (lambda x : '“%s”' % x)
abbr = lambda x : ('~%s' % x[len(home):] if x.startswith(home + '/') else x)


root = '%s/.featherweight' % home
if not os.path.exists(root):
    os.makedirs(root)

feeds = None
with touch('%s/feeds' % root) as feeds_flock:
    flock(feeds_flock, False)
    with open('%s/feeds' % root, 'rb') as file:
        feeds = file.read().decode('utf-8', 'error')
    if len(feeds) == 0:
        feeds = '[]'
    feeds = eval(feeds)
    
    if update:
        group = None
        for arg in args:
            if not arg.startswith('-'):
                group = arg
                break
        
        def update_feed(feed, if_group):
            if 'inner' in feed:
                for feed in feed['inner']:
                    update_feed(feed, if_group)
            elif (if_group is None) or (feed['group'] == if_group):
                pass # TODO update feed
        
        for feed in feeds:
            update_feed(feed, group)
        
        updated = str(feeds)
        with open('%s/feeds' % root, 'wb') as file:
            file.write(updated.encode('utf-8'))
    
    unflock(feeds_flock)


if system:
    sys.exit(0)

print('\033[?1049h\033[?25l\033[?9h', end = '', flush = True)


terminated = False

def update_feeds(function):
    global terminated
    with touch('%s/feeds' % root) as feeds_flock:
        try:
            flock(feeds_flock, True, True)
        except:
            print(_('Feed database is locked by another process, waiting...'))
            flock(feeds_flock, True)
        function(feeds)
        Tree.count_new(feeds)
        _feeds = None
        with open('%s/feeds' % root, 'rb') as file:
            _feeds = file.read().decode('utf-8', 'error')
            with open('%s/feeds.bak' % root, 'wb') as bakfile:
                bakfile.write(str(_feeds).encode('utf-8'))
        if len(_feeds) == 0:
            _feeds = '[]'
        _feeds = eval(_feeds)
        function(_feeds)
        Tree.count_new(_feeds)
        _feeds = str(_feeds)
        try:
            with open('%s/feeds' % root, 'wb') as file:
                file.write(_feeds.encode('utf-8'))
        except Exception as err:
            Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
            print('\n\033[?9l\033[?25h\033[?1049l', end = '', flush = True)
            print('\033[01;31m%s\033[00m', _('Your %s was saved to %s.bak') % ('%s/feeds' % abbr(root), '%s/feeds' % abbr(root)))
            terminated = True
            raise err
        unflock(feeds_flock)


try:
    tree = Tree('My Feeds', feeds)
    while True:
        (action, node) = tree.interact()
        if action == 'quit':
            break
        elif action == 'edit':
            if node is not None:
                print(node)
                sys.stdin.read(1)
                pass
        elif action == 'open':
            print(node)
            sys.stdin.read(1)
            pass
        elif action == 'add':
            if (node is None) or ('url' not in node) or (node['url'] is None) or (node['url'] == ''):
                table = {'Title' : '', 'URL' : ''}
                values = {'id' : str(uuid.uuid4())}
                saved = False
                def saver():
                    global table, values, saved
                    values['title'] = table['Title']
                    values['url'] = None if table['URL'] == '' else table['URL']
                    saved = True
                    return True
                text_area = TextArea(['Title', 'URL'], table)
                text_area.initialise(False)
                print('\033[?25h\033[?9l', end = '', flush = True)
                text_area.run(saver)
                print('\033[?9h\033[?25l', end = '', flush = True)
                text_area.close()
                gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
                gettext.textdomain('@PKGNAME@')
                if saved:
                    update_feeds(lambda t : insert_node(t, node['id'], values))
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
        elif action == 'read':
            if node is not None:
                pass # we do not have entires, just feeds, nothing to read
        elif action == 'unread':
            if node is not None:
                pass # we do not have entires, just feeds, nothing to unread
        elif action == 'back':
            pass # we are at the first page

except Exception as err:
    raise err
    pass
finally:
    if not terminated:
        Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
        print('\n\033[?9l\033[?25h\033[?1049l', end = '', flush = True)

