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
import sys
from subprocess import Popen, PIPE


'''
GNU Emacs alike text area
'''
class TextArea(): # TODO support small screens
    def __init__(self, fields, datamap, left, top, width, height):
        '''
        Constructor
        
        @param  fields:list<str>        Field names
        @param  datamap:dist<str, str>  Data map
        @param  left:int                Left position of the component
        @param  top:int                 Top position of the component
        @param  width:int               Width of the component
        @param  height:int              Height of the component
        '''
        self.fields, self.datamap, self.left, self.top, self.width, self.height = fields, datamap, left, top, width, height
    
    
    
    def run(self, saver):
        '''
        Execute text reading
        
        @param  saver  Save method
        '''
        innerleft = len(max(self.fields, key = len)) + self.left + 3
        
        leftlines = []
        datalines = []
        
        for key in self.fields:
            leftlines.append(key)
            datalines.append(self.datamap[key])
        
        (y, x) = (0, 0)
        mark = None
        
        KILL_MAX = 50
        killring = []
        killptr = None
        
        def status(text):
            print('\033[%i;%iH\033[7m%s\033[27m\033[%i;%iH' % (self.height - 1, 1, ' (' + text + ') ' + '-' * (self.width - len(' (' + text + ') ')), self.top + y, innerleft + x), end='')
        
        status('unmodified')
        
        print('\033[%i;%iH' % (self.top, innerleft), end='')
        
        def alert(text):
            if text is None:
                alert('')
            else:
                print('\033[%i;%iH\033[2K%s\033[%i;%iH' % (self.height, 1, text, self.top + y, innerleft + x), end='')
        
        modified = False
        override = False
        
        (oldy, oldx, oldmark) = (y, x, mark)
        stored = chr(ord('L') - ord('@'))
        alerted = False
        edited = False
        print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
        
        def t(y, x1, x2):
            return datalines[y][x1 : x2]
        
        while True:
            if (oldmark is not None) and (oldmark >= 0):
                if oldmark < oldx:
                    print('\033[%i;%iH\033[49m%s\033[%i;%iH' % (self.top + oldy, innerleft + oldmark, t(oldy, oldmark, oldx), self.top + y, innerleft + x), end='')
                elif oldmark > oldx:
                    print('\033[%i;%iH\033[49m%s\033[%i;%iH' % (self.top + oldy, innerleft + oldx, t(oldy, oldx, oldmark), self.top + y, innerleft + x), end='')
            if (mark is not None) and (mark >= 0):
                if mark < x:
                    print('\033[%i;%iH\033[44;37m%s\033[49;39m\033[%i;%iH' % (self.top + y, innerleft + mark, t(y, mark, x), self.top + y, innerleft + x), end='')
                elif mark > x:
                    print('\033[%i;%iH\033[44;37m%s\033[49;39m\033[%i;%iH' % (self.top + y, innerleft + x, t(y, x, mark), self.top + y, innerleft + x), end='')
            if y != oldy:
                if (oldy > 0) and (leftlines[oldy - 1] == leftlines[oldy]) and (leftlines[oldy] == leftlines[-1]):
                    print('\033[%i;%iH\033[34m%s\033[39m' % (self.top + oldy, self.left, '>'), end='')
                else:
                    print('\033[%i;%iH\033[34m%s:\033[39m' % (self.top + oldy, self.left, leftlines[oldy]), end='')
                if (y > 0) and (leftlines[y - 1] == leftlines[y]) and (leftlines[y] == leftlines[-1]):
                    print('\033[%i;%iH\033[1;34m%s\033[21;39m' % (self.top + y, self.left, '>'), end='')
                else:
                    print('\033[%i;%iH\033[1;34m%s:\033[21;39m' % (self.top + y, self.left, leftlines[y]), end='')
                print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
            (oldy, oldx, oldmark) = (y, x, mark)
            if edited:
                edited = False
                if not modified:
                    modified = True
                    status('modified' + (' override' if override else ''))
            sys.stdout.flush()
            if stored is None:
                d = sys.stdin.read(1)
            else:
                d = stored
                stored = None
            if alerted:
                alerted = False
                alert(None)
            if ord(d) == ord('@') - ord('@'):
                if mark is None:
                    mark = x
                    alert('Mark set')
                elif mark == ~x:
                    mark = x
                    alert('Mark activated')
                elif mark == x:
                    mark = ~x
                    alert('Mark deactivated')
                else:
                    mark = x
                    alert('Mark set')
                alerted = True
            elif ord(d) == ord('K') - ord('@'):
                if x == len(datalines[y]):
                    alert('At end')
                    alerted = True
                else:
                    mark = len(datalines[y])
                    stored = chr(ord('W') - ord('@'))
            elif ord(d) == ord('W') - ord('@'):
                if (mark is not None) and (mark >= 0) and (mark != x):
                    selected = datalines[y][mark : x] if mark < x else datalines[y][x : mark]
                    killring.append(selected)
                    if len(killring) > KILL_MAX:
                        killring = killring[1:]
                    stored = chr(127)
                else:
                    alert('No text is selected')
                    alerted = True
            elif ord(d) == ord('Y') - ord('@'):
                if len(killring) == 0:
                    alert('Killring is empty')
                    alerted = True
                else:
                    mark = None
                    killptr = len(killring) - 1
                    yanked = killring[killptr]
                    print('\033[%i;%iH%s' % (self.top + y, innerleft + x, yanked + datalines[y][x:]), end='')
                    datalines[y] = datalines[y][:x] + yanked + datalines[y][x:]
                    x += len(yanked)
                    print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
            elif ord(d) == ord('X') - ord('@'):
                alert('C-x')
                alerted = True
                sys.stdout.flush()
                d = sys.stdin.read(1)
                alert(str(ord(d)))
                sys.stdout.flush()
                if ord(d) == ord('X') - ord('@'):
                    if (mark is not None) and (mark >= 0):
                        x ^= mark; mark ^= x; x ^= mark
                        alert('Mark swapped')
                    else:
                        alert('No mark is activated')
                elif ord(d) == ord('S') - ord('@'):
                    last = ''
                    for row in range(0, len(datalines)):
                        self.datamap[leftlines[row]] = datalines[row]
                    saver()
                    status('unmodified' + (' override' if override else ''))
                    alert('Saved')
                elif ord(d) == ord('C') - ord('@'):
                    break
                else:
                    stored = d
                    alerted = False
                    alert(None)
            elif (ord(d) == 127) or (ord(d) == 8):
                removed = 1
                if (mark is not None) and (mark >= 0) and (mark != x):
                    if mark > x:
                        x ^= mark; mark ^= x; x ^= mark
                    removed = x - mark
                if x == 0:
                    alert('At beginning')
                    alerted = True
                    continue
                dataline = datalines[y]
                datalines[y] = dataline = dataline[:x - removed] + dataline[x:]
                x -= removed
                mark = None
                print('\033[%i;%iH%s%s\033[%i;%iH' % (self.top + y, innerleft, dataline, ' ' * removed, self.top + y, innerleft + x), end='')
                edited = True
            elif ord(d) < ord(' '):
                if ord(d) == ord('P') - ord('@'):
                    if y == 0:
                        alert('At first line')
                        alerted = True
                    else:
                        y -= 1
                        mark = None
                        x = 0
                elif ord(d) == ord('N') - ord('@'):
                    if y < len(datalines) - 1:
                        y += 1
                        mark = None
                        x = 0
                elif ord(d) == ord('F') - ord('@'):
                    if x < len(datalines[y]):
                        x += 1
                        print('\033[C', end='')
                    else:
                        alert('At end')
                        alerted = True
                elif ord(d) == ord('B') - ord('@'):
                    if x > 0:
                        x -= 1
                        print('\033[D', end='')
                    else:
                        alert('At beginning')
                        alerted = True
                elif ord(d) == ord('L') - ord('@'):
                    empty = '\033[0m' + (' ' * self.width + '\n') * len(datalines)
                    print('\033[%i;%iH%s' % (self.top, self.left, empty), end='')
                    for row in range(0, len(leftlines)):
                        leftline = leftlines[row] + ':'
                        if (leftlines[row - 1] == leftlines[row]) and (leftlines[row] == leftlines[-1]):
                            leftline = '>'
                        print('\033[%i;%iH\033[%s34m%s\033[%s39m' % (self.top + row, self.left, '1;' if row == y else '', leftline, '21;' if row == y else ''), end='')
                    for row in range(0, len(datalines)):
                        print('\033[%i;%iH%s\033[49m' % (self.top + row, innerleft, datalines[row]), end='')
                    print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
                elif d == '\033':
                    d = sys.stdin.read(1)
                    if d == '[':
                        d = sys.stdin.read(1)
                        if d == 'A':
                            stored = chr(ord('P') - ord('@'))
                        elif d == 'B':
                            if y == len(datalines) - 1:
                                alert('At last line')
                                alerted = True
                            else:
                                stored = chr(ord('N') - ord('@'))
                        elif d == 'C':
                            stored = chr(ord('F') - ord('@'))
                        elif d == 'D':
                            stored = chr(ord('B') - ord('@'))
                        elif d == '2':
                            d = sys.stdin.read(1)
                            if d == '~':
                                override = not override
                                status(('modified' if modified else 'unmodified') + (' override' if override else ''))
                        elif d == '3':
                            d = sys.stdin.read(1)
                            if d == '~':
                                removed = 1
                                if (mark is not None) and (mark >= 0) and (mark != x):
                                    if mark < x:
                                        x ^= mark; mark ^= x; x ^= mark
                                    removed = mark - x
                                dataline = datalines[y]
                                if x == len(dataline):
                                    alert('At end')
                                    alerted = True
                                    continue
                                datalines[y] = dataline = dataline[:x] + dataline[x + removed:]
                                print('\033[%i;%iH%s%s\033[%i;%iH' % (self.top + y, innerleft, dataline, ' ' * removed, self.top + y, innerleft + x), end='')
                                mark = None
                                edited = True
                        else:
                            while True:
                                d = sys.stdin.read(1)
                                if (ord('a') <= ord(d)) and (ord(d) <= ord('z')): break
                                if (ord('A') <= ord(d)) and (ord(d) <= ord('Z')): break
                                if d == '~': break
                    elif (d == 'w') or (d == 'W'):
                        if (mark is not None) and (mark >= 0) and (mark != x):
                            selected = datalines[y][mark : x] if mark < x else datalines[y][x : mark]
                            killring.append(selected)
                            mark = None
                            if len(killring) > KILL_MAX:
                                killring = killring[1:]
                        else:
                            alert('No text is selected')
                            alerted = True
                    elif (d == 'y') or (d == 'Y'):
                        if killptr is not None:
                            yanked = killring[killptr]
                            dataline = datalines[y]
                            if (len(yanked) <= x) and (dataline[x - len(yanked) : x] == yanked):
                                killptr -= 1
                                if killptr < 0:
                                    killptr += len(killring)
                                dataline = dataline[:x - len(yanked)] + killring[killptr] + dataline[x:]
                                additional = len(killring[killptr]) - len(yanked)
                                x += additional
                                datalines[y] = dataline
                                print('\033[%i;%iH%s%s\033[%i;%iH' % (self.top + y, innerleft, dataline, ' ' * max(0, -additional), self.top + y, innerleft + x), end='')
                            else:
                                stored = chr(ord('Y') - ord('@'))
                        else:
                            stored = chr(ord('Y') - ord('@'))
                    elif d == 'O':
                        d = sys.stdin.read(1)
                        if d == 'H':
                            x = 0
                        elif d == 'F':
                            x = len(datalines[y])
                        print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
                elif d == '\n':
                    stored = chr(ord('N') - ord('@'))
            else:
                insert = d
                if len(insert) == 0:
                    continue
                dataline = datalines[y]
                if (not override) or (x == len(dataline)):
                    print(insert + dataline[x:], end='')
                    if len(dataline) - x > 0:
                        print('\033[%iD' % (len(dataline) - x), end='')
                    datalines[y] = dataline[:x] + insert + dataline[x:]
                    if (mark is not None) and (mark >= 0):
                        if mark >= x:
                            mark += len(insert)
                else:
                    print(insert, end='')
                    datalines[y] = dataline[:x] + insert + dataline[x + 1:]
                x += len(insert)
                edited = True


def phonysaver():
    pass
print('\033[H\033[2J')
old_stty = Popen('stty --save'.split(' '), stdout = PIPE).communicate()[0]
old_stty = old_stty.decode('utf-8', 'error')[:-1]
Popen('stty -icanon -echo -isig -ixon -ixoff'.split(' '), stdout = PIPE).communicate()
try:
    TextArea(['alpha', 'beta'], {'alpha' : 'a', 'beta' : 'be'}, 1, 1, 20, 4).run(phonysaver)
finally:
    print('\033[H\033[2J', end = '')
    sys.stdout.flush()
    Popen(['stty', old_stty], stdout = PIPE).communicate()

