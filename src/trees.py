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
        global count, height, width
        
        self.root = root
        self.feeds = feeds
        
        self.islinux = ('TERM' not in os.environ) or (os.environ['TERM'] == 'linux')
        count = self.count_new(feeds)
        
        self.select_stack = [(None, None)]
        self.collapsed_count = 0
        
        height_width = Popen('stty size'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
        (height, width) = height_width.decode('utf-8', 'error')[:-1].split(' ')
        height, width = int(height), int(width)
        
        self.line = 0
        self.curline = 0
        self.lineoff = 0
    
    
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
        global height, width
        title = feed['title']
        prefix = indent + ('└' if last else '├')
        collapsed = False
        if ('inner' not in feed) or (self.is_expanded(feed)):
            prefix += '── ' if self.islinux else '─╼ '
        else:
            collapsed = True
            prefix += '─┘ ' if self.islinux else '─┚ '
        if feed['new'] > 0:
            prefix += '\033[01;31m(%i)\033[00m ' % feed['new']
        prefixlen = len('%s--- %s' % (indent, ('(%i) ' % feed['new']) if feed['new'] > 0 else ''))
        if prefixlen + len(title) > width:
            if width - prefixlen - 3 >= 0:
                title = title[: width - prefixlen - 3] + '...'
        if self.select_stack[-1][0] is feed:
            title = '\033[01;34m%s\033[00m' % title
        if self.lineoff <= self.curline < self.lineoff + height:
            if self.curline > self.lineoff:
                print()
            print(prefix + title, end = '')
        self.curline += 1
        if self.line >= 0:
            self.line += 1
            if self.select_stack[-1][0] is feed:
                self.line = ~self.line
        if ('inner' in feed) and not collapsed:
            inner = feed['inner']
            for feed in inner:
                self.print_node(feed, feed is inner[-1], indent + ('    ' if last else '│   '))
    
    
    def print_tree(self):
        global height, width, count
        self.line = 0
        self.curline = 0
        height_width = Popen('stty size'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
        (height, width) = height_width.decode('utf-8', 'error')[:-1].split(' ')
        height, width = int(height), int(width)
        
        print('\033[H\033[2J', end = '')
        title = self.root
        if len(self.select_stack) == 1:
            title = '\033[01;34m%s\033[00m' % title
        if self.lineoff <= self.curline < self.lineoff + height:
            if count > 0:
                print('\033[01;31m(%i)\033[00m ' % count, end = '')
            print(title, end = '')
        self.line += 1
        self.curline += 1
        if len(self.select_stack) == 1:
            self.line = ~self.line
        for feed in self.feeds:
            self.print_node(feed, feed is self.feeds[-1], '')
        sys.stdout.flush()
        
        self.line = ~self.line
        if not (self.lineoff < self.line <= self.lineoff + height):
            self.lineoff = self.line - height // 2
            if not (self.lineoff < self.line <= self.lineoff + height):
                self.lineoff -= 1
            if self.lineoff < 0:
                self.lineoff = 0
            self.print_tree()
    
    
    def interact(self):
        global height, width
        self.print_tree()
        
        buf = '\0' * 10
        queued = ''
        while True:
            if queued == '':
                buf += chr(sys.stdin.buffer.read(1)[0])
            else:
                buf += queued[:1]
                queued = queued[1:]
            buf = buf[-10:]
            if buf[-4 : -1] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                pass
            elif buf[-5 : -2] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                pass
            elif buf[-6 : -3] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                a, x, y = ord(buf[-3]), ord(buf[-2]), ord(buf[-1])
                if a == 96:
                    queued += '\033[A' * 3
                elif a == 97:
                    queued += '\033[B' * 3
                elif a == 32:
                    y -= 33
                    if y < 0:
                        y += 256
                    line = self.lineoff + y
                    last = self.select_stack[-1][0]
                    backup = self.select_stack[:]
                    self.select_stack[:] = self.select_stack[:1]
                    tline = 0
                    if line > 0:
                        while tline != line:
                            if self.select_stack[-1][0] is None:
                                if len(self.feeds) > 0:
                                    self.select_stack.append((self.feeds[0], 0))
                                    tline += 1
                            else:
                                cur = self.select_stack[-1][0]
                                curi = self.select_stack[-1][1]
                                if ('inner' in cur) and self.is_expanded(cur):
                                    self.select_stack.append((cur['inner'][0], 0))
                                    tline += 1
                                else:
                                    has_next = False
                                    while len(self.select_stack) > 1:
                                        par = self.select_stack[-2][0]
                                        par = self.feeds if par is None else par['inner']
                                        self.select_stack.pop()
                                        if curi + 1 < len(par):
                                            self.select_stack.append((par[curi + 1], curi + 1))
                                            has_next = True
                                            break
                                        cur = self.select_stack[-1][0]
                                        curi = self.select_stack[-1][1]
                                    if not has_next:
                                        break
                                    else:
                                        tline += 1
                        if tline == line:
                            backup = None
                    else:
                        backup = None
                    if backup is None:
                        if self.select_stack[-1][0] is last:
                            if (last is None) or ('inner' in last):
                                queued += ' '
                            else:
                                queued += '\n'
                        else:
                            self.print_tree()
                    else:
                        self.select_stack[:] = backup
            elif buf.endswith('\033[A'):
                if self.select_stack[-1][0] is not None:
                    cur = self.select_stack[-1][0]
                    curi = self.select_stack[-1][1]
                    self.select_stack.pop()
                    if curi > 0:
                        par = self.select_stack[-1][0]
                        par = self.feeds if par is None else par['inner']
                        curi -= 1
                        cur = par[curi]
                        self.select_stack.append((cur, curi))
                        while ('inner' in cur) and self.is_expanded(cur):
                            curi = len(cur['inner']) - 1
                            cur = cur['inner'][curi]
                            self.select_stack.append((cur, curi))
                    self.print_tree()
            elif buf.endswith('\033[1;5A'):
                if self.select_stack[-1][0] is not None:
                    cur = self.select_stack[-1][0]
                    curi = self.select_stack[-1][1]
                    self.select_stack.pop()
                    if curi > 0:
                        par = self.select_stack[-1][0]
                        par = self.feeds if par is None else par['inner']
                        self.select_stack.append((par[curi - 1], curi - 1))
                    self.print_tree()
            elif buf.endswith('\033[B'):
                if self.select_stack[-1][0] is None:
                    if len(self.feeds) > 0:
                        self.select_stack.append((self.feeds[0], 0))
                        self.print_tree()
                else:
                    cur = self.select_stack[-1][0]
                    curi = self.select_stack[-1][1]
                    if ('inner' in cur) and self.is_expanded(cur):
                        self.select_stack.append((cur['inner'][0], 0))
                        self.print_tree()
                    else:
                        backup = self.select_stack[:]
                        while len(self.select_stack) > 1:
                            par = self.select_stack[-2][0]
                            par = self.feeds if par is None else par['inner']
                            self.select_stack.pop()
                            if curi + 1 < len(par):
                                self.select_stack.append((par[curi + 1], curi + 1))
                                backup = None
                                self.print_tree()
                                break
                            cur = self.select_stack[-1][0]
                            curi = self.select_stack[-1][1]
                        if backup is not None:
                            self.select_stack[:] = backup
            elif buf.endswith('\033[1;5B'):
                while self.select_stack[-1][0] is not None:
                    cur = self.select_stack[-1][0]
                    curi = self.select_stack[-1][1]
                    par = self.select_stack[-2][0]
                    par = self.feeds if par is None else par['inner']
                    if curi + 1 < len(par):
                        self.select_stack.pop()
                        self.select_stack.append((par[curi + 1], curi + 1))
                        self.print_tree()
                        break
                    elif self.select_stack[-2][0] is not None:
                        self.select_stack.pop()
                    else:
                        break
            elif buf.endswith('\033[C'):
                if self.select_stack[-1][0] is None:
                    if len(self.feeds) > 0:
                        self.select_stack.append((self.feeds[0], 0))
                        self.print_tree()
                else:
                    cur = self.select_stack[-1][0]
                    curi = self.select_stack[-1][1]
                    if 'inner' in cur:
                        if not self.is_expanded(cur):
                            cur['expanded'] = True
                            self.collapsed_count -= 1
                        self.select_stack.append((cur['inner'][0], 0))
                        self.print_tree()
            elif buf.endswith('\033[D'):
                if len(self.select_stack) > 1:
                    self.select_stack.pop()
                    self.print_tree()
            elif buf.endswith('\033[1;5D'):
                self.select_stack[:] = self.select_stack[:1]
                self.print_tree()
            elif buf.endswith(' '):
                cur = self.select_stack[-1][0]
                if cur is None:
                    def expand(feed, value):
                        if 'inner' in feed:
                            cur_value = self.is_expanded(feed)
                            if cur_value != value:
                                feed['expanded'] = value
                                self.collapsed_count += -1 if value else 1
                            for inner in feed['inner']:
                                expand(inner, value)
                    value = self.collapsed_count != 0
                    for feed in self.feeds:
                        expand(feed, value)
                else:
                    if 'inner' in cur:
                        value = not self.is_expanded(cur)
                        self.collapsed_count += -1 if value else 1
                        cur['expanded'] = value
                self.print_tree()
            elif buf.endswith(chr(ord('L') - ord('@'))):
                self.print_tree()
            elif buf.endswith('q'):
                return ('quit', None)
            elif buf.endswith('e'):
                return ('edit', self.select_stack[-1][0])
            elif buf.endswith('+'):
                return ('add', self.select_stack[-1][0])
            elif buf.endswith('d'):
                return ('delete', self.select_stack[-1][0])
            elif buf.endswith('r'):
                return ('read', self.select_stack[-1][0])
            elif buf.endswith('R'):
                return ('unread', self.select_stack[-1][0])
            elif ord('0') <= ord(buf[-1]) <= ord('9'):
                return (buf[-1], self.select_stack[-1][0])
            elif buf.endswith('\t'):
                return ('back', None)
            elif buf.endswith('\n'):
                return ('open', self.select_stack[-1][0])

