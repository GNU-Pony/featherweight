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
    prefix = indent + ('└' if last else '├') + ('── ' if islinux else '─╼ ')
    if feed['new'] > 0:
        prefix += '\033[01;31m(%i)\033[00m ' % feed['new']
    print(prefix + title)
    if 'inner' in feed:
        inner = feed['inner']
        for feed in inner:
            print_node(feed, feed is inner[-1], indent + ('    ' if last else '│   '))


count = count_new(feeds)
if count > 0:
    print('\033[01;31m(%i)\033[00m' % count, end = ' ')
print('My Feeds')
for feed in feeds:
    print_node(feed, feed is feeds[-1], '')

