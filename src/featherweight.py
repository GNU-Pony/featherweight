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
from subprocess import Popen, PIPE

from flocker import *
from trees import *


old_stty = Popen('stty --save'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
old_stty = old_stty.decode('utf-8', 'error')[:-1]

Popen('stty -icanon -echo'.split(' '), stdout = PIPE, stderr = PIPE).communicate()


args = sys.argv[1:]
update = '--update' in args
system = '--system' in args


home = os.environ['HOME']
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
                uuid = feed['uuid']
                with touch('%s/%s' % (root, uuid)) as feed_flock:
                    flock(feed_flock, True)
                    feed_info = None
                    with open('%s/%s' % (root, uuid), 'rb') as file:
                        feed_info = file.read().decode('utf-8', 'error')
                    feed_info = eval(feed_info)
                    have = feed_info['have']
                    unread = feed_info['unread']
                    
                    ## TODO update feed
                    
                    feed['new'] = len(unread)
                    with open('%s/%s' % (root, uuid), 'wb') as file:
                        file.write(str(feed_info).decode('utf-8'))
                        file.flush()
                    unflock(feed_flock)
        
        for feed in feeds:
            update_feed(feed, group)
        
        updated = str(feeds)
        with open('%s/feeds' % root, 'wb') as file:
            file.write(updated.encode('utf-8'))
    
    unflock(feeds_flock)


if system:
    sys.exit(0)

print('\033[?1049h\033[?25l\033[?9h', end = '')

try:
    tree = Tree('My Feeds', feeds)
    while True:
        (action, node) = tree.interact()
        if action == 'quit':
            break
        elif action == 'edit':
            if node is not None:
                pass
        elif action == 'open':
            pass

except Exception as err:
    raise err
    pass
finally:
    Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
    print('\n\033[?9l\033[?25h\033[?1049l', end = '')

