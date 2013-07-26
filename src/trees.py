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


class Tree():
    def __init__(self, root, feeds):
        global islinux, count, height, width, line, curline, lineoff, collapsed_count, select_stack
        
        self.root = root
        self.feeds = feeds
        
        islinux = ('TERM' not in os.environ) or (os.environ['TERM'] == 'linux')
        count = self.count_new(feeds)
        
        select_stack = [(None, None)]
        collapsed_count = 0
        
        height_width = Popen('stty size'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
        (height, width) = height_width.decode('utf-8', 'error')[:-1].split(' ')
        height, width = int(height), int(width)
        
        line = 0
        curline = 0
        lineoff = 0
    
    
    def count_new(self, feeds):
        rc = 0
        for feed in feeds:
            count = 0
            if 'inner' in feed:
                count = self.count_new(feed['inner'])
                feed['new'] = count
            else:
                count = feed['new']
            rc += count
        return rc
    
    
    def is_expanded(self, feed):
        return ('expanded' not in feed) or feed['expanded']
    
    
    def print_node(self, feed, last, indent):
        global line, curline, lineoff, height, islinux, select_stack
        title = feed['title']
        prefix = indent + ('└' if last else '├')
        collapsed = False
        if ('inner' not in feed) or (self.is_expanded(feed)):
            prefix += '── ' if islinux else '─╼ '
        else:
            collapsed = True
            prefix += '─┘ ' if islinux else '─┚ '
        if feed['new'] > 0:
            prefix += '\033[01;31m(%i)\033[00m ' % feed['new']
        if select_stack[-1][0] is feed:
            title = '\033[01;34m%s\033[00m' % title
        if lineoff <= curline < lineoff + height:
            if curline > lineoff:
                print()
            print(prefix + title, end = '')
        curline += 1
        if line >= 0:
            line += 1
            if select_stack[-1][0] is feed:
                line = ~line
        if ('inner' in feed) and not collapsed:
            inner = feed['inner']
            for feed in inner:
                self.print_node(feed, feed is inner[-1], indent + ('    ' if last else '│   '))
    
    
    def print_tree(self):
        global line, curline, lineoff, height, width, count, select_stack
        line = 0
        curline = 0
        height_width = Popen('stty size'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
        (height, width) = height_width.decode('utf-8', 'error')[:-1].split(' ')
        height, width = int(height), int(width)
        
        print('\033[H\033[2J', end = '')
        title = self.root
        if len(select_stack) == 1:
            title = '\033[01;34m%s\033[00m' % title
        if lineoff <= curline < lineoff + height:
            if count > 0:
                print('\033[01;31m(%i)\033[00m ' % count, end = '')
            print(title, end = '')
        line += 1
        curline += 1
        if len(select_stack) == 1:
            line = ~line
        for feed in self.feeds:
            self.print_node(feed, feed is self.feeds[-1], '')
        sys.stdout.flush()
        
        line = ~line
        if not (lineoff < line <= lineoff + height):
            lineoff = line - height // 2
            if not (lineoff < line <= lineoff + height):
                lineoff -= 1
            if lineoff < 0:
                lineoff = 0
            self.print_tree()
    
    
    def interact(self):
        global height, width, line, curline, lineoff, collapsed_count, select_stack
        self.print_tree()
        
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
                        par = self.feeds if par is None else par['inner']
                        curi -= 1
                        cur = par[curi]
                        select_stack.append((cur, curi))
                        while ('inner' in cur) and self.is_expanded(cur):
                            curi = len(cur['inner']) - 1
                            cur = cur['inner'][curi]
                            select_stack.append((cur, curi))
                    self.print_tree()
            elif buf.endswith('\033[1;5A'):
                if select_stack[-1][0] is not None:
                    cur = select_stack[-1][0]
                    curi = select_stack[-1][1]
                    select_stack.pop()
                    if curi > 0:
                        par = select_stack[-1][0]
                        par = self.feeds if par is None else par['inner']
                        select_stack.append((par[curi - 1], curi - 1))
                    self.print_tree()
            elif buf.endswith('\033[B'):
                if select_stack[-1][0] is None:
                    if len(self.feeds) > 0:
                        select_stack.append((self.feeds[0], 0))
                        self.print_tree()
                else:
                    cur = select_stack[-1][0]
                    curi = select_stack[-1][1]
                    if ('inner' in cur) and self.is_expanded(cur):
                        select_stack.append((cur['inner'][0], 0))
                        self.print_tree()
                    else:
                        backup = select_stack[:]
                        while len(select_stack) > 1:
                            par = select_stack[-2][0]
                            par = self.feeds if par is None else par['inner']
                            select_stack.pop()
                            if curi + 1 < len(par):
                                select_stack.append((par[curi + 1], curi + 1))
                                backup = None
                                self.print_tree()
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
                    par = self.feeds if par is None else par['inner']
                    if curi + 1 < len(par):
                        select_stack.pop()
                        select_stack.append((par[curi + 1], curi + 1))
                        self.print_tree()
                        break
                    elif select_stack[-2][0] is not None:
                        select_stack.pop()
                    else:
                        break
            elif buf.endswith('\033[C'):
                if select_stack[-1][0] is None:
                    if len(self.feeds) > 0:
                        select_stack.append((self.feeds[0], 0))
                        self.print_tree()
                else:
                    cur = select_stack[-1][0]
                    curi = select_stack[-1][1]
                    if 'inner' in cur:
                        if not self.is_expanded(cur):
                            cur['expanded'] = True
                            collapsed_count -= 1
                        select_stack.append((cur['inner'][0], 0))
                        self.print_tree()
            elif buf.endswith('\033[D'):
                if len(select_stack) > 1:
                    select_stack.pop()
                    self.print_tree()
            elif buf.endswith('\033[1;5D'):
                select_stack[:] = select_stack[:1]
                self.print_tree()
            elif buf.endswith(' '):
                cur = select_stack[-1][0]
                if cur is None:
                    def expand(feed, value):
                        global collapsed_count
                        if 'inner' in feed:
                            cur_value = self.is_expanded(feed)
                            if cur_value != value:
                                feed['expanded'] = value
                                collapsed_count += -1 if value else 1
                            for inner in feed['inner']:
                                expand(inner, value)
                    value = collapsed_count != 0
                    for feed in self.feeds:
                        expand(feed, value)
                else:
                    if 'inner' in cur:
                        value = not self.is_expanded(cur)
                        collapsed_count += -1 if value else 1
                        cur['expanded'] = value
                self.print_tree()
            elif buf.endswith(chr(ord('L') - ord('@'))):
                self.print_tree()
            elif buf.endswith('q'):
                break
            elif buf.endswith('\t'):
                print('Tab')
            elif buf.endswith('\n'):
                print('Enter')

