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
    unflock(feeds_flock)


print('\033[?1049h\033[?25l', end = '')

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

except:
    pass
finally:
    Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
    print('\033[?25h\033[?1049l', end = '')

