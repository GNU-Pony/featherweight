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


height_width = Popen('stty size'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
(height, width) = height_width.decode('utf-8', 'error')[:-1].split(' ')

old_stty = Popen('stty --save'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
old_stty = old_stty.decode('utf-8', 'error')[:-1]

Popen('stty -icanon -echo'.split(' '), stdout = PIPE, stderr = PIPE).communicate()


home = os.environ['HOME']
root = '%s/.featherweight' % home
if not os.path.exists(root):
    os.makedirs(root)

islinux = ('TERM' not in os.environ) or (os.environ['TERM'] == 'linux')

feeds = None
with touch('%s/feeds' % root) as feeds_flock:
    flock(feeds_flock, False)
    with open('%s/feeds' % root, 'rb') as file:
        feeds = file.read().decode('utf-8', 'error')
    if len(feeds) == 0:
        feeds = '[]'
    feeds = eval(feeds)
    unflock(feeds_flock)


def count_new(feeds):
    rc = 0
    for feed in feeds:
        count = 0
        if 'inner' in feed:
            count = count_new(feed['inner'])
            feed['new'] = count
        else:
            count = feed['new']
        rc += count
    return rc


def print_node(feed, last, indent):
    title = feed['title']
    prefix = indent + ('└' if last else '├')
    collapsed = False
    if ('inner' not in feed) or (('expanded' not in feed) or feed['expanded']):
        prefix += '── ' if islinux else '─╼ '
    else:
        collapsed = True
        prefix += '─┘ ' if islinux else '─┚ '
    if feed['new'] > 0:
        prefix += '\033[01;31m(%i)\033[00m ' % feed['new']
    if select_stack[-1][0] == feed:
        title = '\033[01;34m%s\033[00m' % title
    print(prefix + title)
    if ('inner' in feed) and not collapsed:
        inner = feed['inner']
        for feed in inner:
            print_node(feed, feed is inner[-1], indent + ('    ' if last else '│   '))


count = count_new(feeds)

def print_tree():
    print('\033[H\033[2J', end = '')
    if count > 0:
        print('\033[01;31m(%i)\033[00m' % count, end = ' ')
    title = 'My Feeds'
    if len(select_stack) == 1:
        title = '\033[01;34m%s\033[00m' % title
    print(title)
    for feed in feeds:
        print_node(feed, feed is feeds[-1], '')


print('\033[?1049h\033[?25l', end = '')
select_stack = [(None, None)]
global collapsed_count
collapsed_count = 0
print_tree()

try:
    buf = ''
    while True:
        buf += sys.stdin.read(1)
        buf = buf[-10:]
        if buf.endswith('\033[A'):
            if select_stack[-1][0] is not None:
                cur = select_stack[-1][0]
                curi = select_stack[-1][1]
                select_stack.pop()
                if curi > 0:
                    par = select_stack[-1][0]
                    par = feeds if par is None else par['inner']
                    curi -= 1
                    cur = par[curi]
                    select_stack.append((cur, curi))
                    while 'inner' in cur:
                        curi = len(cur['inner']) - 1
                        cur = cur['inner'][curi]
                        select_stack.append((cur, curi))
                print_tree()
        elif buf.endswith('\033[1;5A'):
            if select_stack[-1][0] is not None:
                cur = select_stack[-1][0]
                curi = select_stack[-1][1]
                select_stack.pop()
                if curi > 0:
                    par = select_stack[-1][0]
                    par = feeds if par is None else par['inner']
                    select_stack.append((par[curi - 1], curi - 1))
                print_tree()
        elif buf.endswith('\033[B'):
            if select_stack[-1][0] is None:
                if len(feeds) > 0:
                    select_stack.append((feeds[0], 0))
                    print_tree()
            else:
                cur = select_stack[-1][0]
                curi = select_stack[-1][1]
                if 'inner' in cur:
                    select_stack.append((cur['inner'][0], 0))
                    print_tree()
                else:
                    backup = select_stack[:]
                    while len(select_stack) > 1:
                        par = select_stack[-2][0]
                        par = feeds if par is None else par['inner']
                        select_stack.pop()
                        if curi + 1 < len(par):
                            select_stack.append((par[curi + 1], curi + 1))
                            backup = None
                            print_tree()
                            break
                        cur = select_stack[-1][0]
                        curi = select_stack[-1][1]
                    if backup is not None:
                        select_stack[:] = backup
        elif buf.endswith('\033[1;5B'):
            while select_stack[-1][0] is not None:
                cur = select_stack[-1][0]
                curi = select_stack[-1][1]
                par = select_stack[-2][0]
                par = feeds if par is None else par['inner']
                if curi + 1 < len(par):
                    select_stack.pop()
                    select_stack.append((par[curi + 1], curi + 1))
                    print_tree()
                    break
                elif select_stack[-2][0] is not None:
                    select_stack.pop()
                else:
                    break
        elif buf.endswith('\033[C'):
            if select_stack[-1][0] is None:
                if len(feeds) > 0:
                    select_stack.append((feeds[0], 0))
                    print_tree()
            else:
                cur = select_stack[-1][0]
                curi = select_stack[-1][1]
                if 'inner' in cur:
                    select_stack.append((cur['inner'][0], 0))
                    print_tree()
        elif buf.endswith('\033[D'):
            if len(select_stack) > 1:
                select_stack.pop()
                print_tree()
        elif buf.endswith('\033[1;5D'):
            select_stack[:] = select_stack[:1]
            print_tree()
        elif buf.endswith(' '):
            cur = select_stack[-1][0]
            if cur is None:
                def expand(feed, value):
                    global collapsed_count
                    if 'inner' in feed:
                        cur_value = (('expanded' not in feed) or feed['expanded'])
                        if cur_value != value:
                            feed['expanded'] = value
                            collapsed_count += -1 if value else 1
                        for inner in feed['inner']:
                            expand(inner, value)
                value = collapsed_count != 0
                for feed in feeds:
                    expand(feed, value)
            else:
                if 'inner' in cur:
                    value = not (('expanded' not in cur) or cur['expanded'])
                    collapsed_count += -1 if value else 1
                    cur['expanded'] = value
            print_tree()
            print('Space')
        elif buf.endswith('\t'):
            print('Tab')
        elif buf.endswith('\n'):
            print('Enter')
    
except Exception as err:
    raise err
    pass
finally:
    Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
    print('\033[?25h\033[?1049l', end = '')

