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
class TextArea():
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
        self.fields, self.datamap, self.left, self.top, self.width, self.height = fields, datamap, left, top, width - 1, height
        self.innerleft = len(max(self.fields, key = len)) + 3
        self.lines = [TextArea.Line(self, self.fields[y], self.datamap[self.fields[y]], y) for y in range(len(self.fields))]
        self.areawidth = self.width - self.innerleft - self.left + 1
        self.killring, self.killmax, self.killptr = [], 50, 0
        self.y, self.x, self.offx, self.mark = 0, 0, 0, None
        self.last_alert, self.last_status, self.alerted = None, None, False
    
    
    def get_selection(self, for_display = False):
        a = min(self.mark, self.x)
        b = max(self.mark, self.x)
        if for_display:
            a = min(max(a - self.offx, 0), self.areawidth)
            b = min(max(b - self.offx, 0), self.areawidth)
        return (a, b)
    
    
    class Line():
        def __init__(self, area, name, text, y):
            self.area, self.name, self.text, self.y = area, name, text, y
        
        def draw(self):
            leftside = '\033[%i;%iH\033[%s34m%s:\033[00m' % (self.area.top + self.y, self.area.left, '01;' if self.area.y == self.y else '', self.name)
            text = (self.text[self.area.offx if self.area.y == self.y else 0:] + ' ' * self.area.areawidth)[:self.area.areawidth]
            if (self.area.y == self.y) and (self.area.mark is not None) and (self.area.mark >= 0):
                (a, b) = self.area.get_selection(True)
                if a != b:
                    text = text[:a] + ('\033[44;37m%s\033[00m' % text[a : b]) + text[b:]
            print('%s\033[%i;%iH%s' % (leftside, self.area.top + self.y, self.area.left + self.area.innerleft, text), end='')
        
        def copy(self):
            if (self.area.mark is not None) and (self.area.mark >= 0) and (self.area.mark != self.area.x):
                (a, b) = self.area.get_selection()
                self.area.killring.append(self.text[a : b])
                if len(self.area.killring) > self.area.killmax:
                    self.area.killring[:] = self.area.killring[1:]
                (a, b) = self.area.get_selection(True)
                text = self.text[self.area.offx:][:self.area.areawidth][a : b]
                print('\033[%i;%iH%s' % (self.area.top + self.y, self.area.left + self.area.innerleft + a, text), end='')
                self.area.mark = None
                return True
            else:
                return False
        
        def cut(self):
            mark, x = self.area.mark, self.area.x
            if self.copy():
                self.area.mark, self.area.x = mark, x
                self.delete()
                return True
            else:
                return False
        
        def kill(self):
            if self.area.x < len(self.text):
                self.area.mark = len(self.text)
                self.cut()
                return True
            else:
                return False
        
        def delete(self):
            removed = 0
            if (self.area.mark is not None) and (self.area.mark >= 0) and (self.area.mark != self.area.x):
                (a, b) = self.area.get_selection()
                self.text = self.text[:a] + self.text[b:]
                self.area.x = a
                if self.area.offx > len(self.text):
                    self.area.offx = max(len(self.text) - self.area.areawidth, 0)
                    self.area.mark = None
                    print('\033[%i;%iH%s' % (self.area.top + self.y, self.area.left + self.area.innerleft, ' ' * self.area.areawidth), end='')
                    self.draw()
                    return True
                removed = b - a
            self.area.mark = None
            if removed == 0:
                if self.area.x == len(self.text):
                    return False
                removed = 1
                self.text = self.text[:self.area.x] + self.text[self.area.x + 1:]
            text = self.text[self.area.offx:][:self.area.areawidth]
            a = min(max(self.area.x - self.area.offx, 0), self.area.areawidth)
            left = self.area.left + self.area.innerleft + a
            print('\033[%i;%iH%s\033[%i;%iH' % (self.area.top + self.y, left, text[a:] + ' ' * removed, self.area.top + self.y, left), end='')
            return True
        
        def erase(self):
            if not ((self.area.mark is not None) and (self.area.mark >= 0) and (self.area.mark != self.area.x)):
                self.area.mark = None
                if self.area.x == 0:
                    return False
                self.area.x -= 1
                if self.area.x < self.area.offx:
                    self.area.offx = max(self.area.offx - self.area.areawidth, 0)
                    self.draw()
                    print('\033[%i;%iH' % (self.area.top + self.y, self.area.left + self.area.innerleft + self.area.x - self.area.offx), end='')
            self.delete()
            return True
        
        def yank(self, resetptr = True):
            if len(self.area.killring) == 0:
                return False
            self.area.mark = None
            if resetptr:
                self.area.killptr = len(self.area.killring) - 1
            yanked = self.area.killring[self.area.killptr]
            self.text = self.text[:self.area.x] + self.area.killring[self.area.killptr] + self.text[self.area.x:]
            self.area.x += len(yanked)
            if self.area.x > self.area.offx + self.area.areawidth:
                self.area.offx = len(self.text) - self.area.areawidth
            print('\033[%i;%iH%s' % (self.area.top + self.y, self.area.left + self.area.innerleft, ' ' * self.area.areawidth), end='')
            self.draw()
            print('\033[%i;%iH' % (self.area.top + self.y, self.area.left + self.area.innerleft + self.area.x - self.area.offx), end='')
            return True
        
        def yank_cycle(self):
            if len(self.area.killring) == 0:
                return False
            yanked = self.area.killring[self.area.killptr]
            if self.text[max(self.area.x - len(yanked), 0) : self.area.x] != yanked:
                return False
            self.area.mark = self.area.x - len(yanked)
            self.delete()
            self.area.killptr -= 1
            self.yank(self.area.killptr < 0)
            return True
        
        def move_point(self, delta):
            x = self.area.x + delta
            if 0 <= x <= len(self.text):
                self.area.x = x
                if delta < 0:
                    if self.area.offx > self.area.x:
                        self.area.offx = self.area.x - self.area.areawidth
                        self.area.offx = max(self.area.offx, 0)
                        self.draw()
                        print('\033[%i;%iH' % (self.area.top + self.y, self.area.left + self.area.innerleft + self.area.x - self.area.offx), end='')
                    else:
                        print('\033[%iD' % -delta, end='')
                elif delta > 0:
                    if self.area.x - self.area.offx > self.area.areawidth:
                        self.area.offx = self.area.x
                        self.draw()
                        print('\033[%i;%iH' % (self.area.top + self.y, self.area.left + self.area.innerleft), end='')
                    else:
                        print('\033[%iC' % delta, end='')
                return delta != 0
            return False
        
        def swap_mark(self):
            if (self.area.mark is not None) and (self.area.mark >= 0):
                self.area.mark, self.area.x = self.area.x, self.area.mark
                return True
            else:
                return False
        
        def override(self, insert, override = True):
            if (self.area.mark is not None) and (self.area.mark >= 0):
                self.area.mark = ~(self.area.mark)
            if len(insert) == 0:
                return
            a, b = self.area.x, self.area.x
            if override:
                b = min(self.area.x + len(insert), len(self.text))
            self.text = self.text[:a] + insert + self.text[b:]
            oldx = self.area.x
            self.area.x += len(insert)
            if self.area.x - self.area.offx < self.area.areawidth:
                if not override:
                    y = self.area.top + self.y
                    xi = self.area.left + self.area.innerleft
                    print('\033[%i;%iH\033[%iP' % (y, xi + self.area.areawidth - len(insert), len(insert)), end='')
                    print('\033[%i;%iH\033[%i@' % (y, xi + oldx - self.area.offx, len(insert)), end='')
                print(insert, end='')
            else:
                self.area.offx = len(self.text) - self.area.areawidth
                print('\033[%i;%iH%s' % (self.area.top + self.y, self.area.left + self.area.innerleft, ' ' * self.area.areawidth), end='')
                self.draw()
                print('\033[%i;%iH' % (self.area.top + self.y, self.area.left + self.area.innerleft + self.area.x - self.area.offx), end='')
        
        def insert(self, insert):
            self.override(insert, False)
    
    
    
    def status(self, text):
        txt = ' (' + text + ') '
        y = self.top + self.y
        x = self.left + self.innerleft + self.x - self.offx
        print('\033[%i;%iH\033[7m%s-\033[27m\033[%i;%iH' % (self.height - 1, 1, txt + '-' * (self.width - len(txt)), y, x), end='')
        self.last_status = text
    
    def alert(self, text):
        if text is None:
            self.alert('')
            self.alerted = False
        else:
            y = self.top + self.y
            x = self.left + self.innerleft + self.x - self.offx
            print('\033[%i;%iH\033[2K%s\033[%i;%iH' % (self.height, 1, text, y, x), end='')
            self.alerted = True
        self.last_alert = text
    
    def restatus(self):
        self.status(self.last_status)
    
    def realert(self):
        self.alert(self.last_alert)
    
    
    def run(self, saver, preredrawer, postredrawer):
        '''
        Execute text reading
        
        @param  saver  Save method
        '''
        
        self.status('unmodified')
        
        modified = False
        override = False
        
        oldy, oldx, oldmark = self.y, self.x, self.mark
        stored = chr(ord('L') - ord('@'))
        edited = False
        
        while True:
            if ((oldmark is not None) and (oldmark >= 0)) or ((self.mark is not None) and (self.mark >= 0)):
                self.lines[self.y].draw()
            if self.y != oldy:
                self.lines[oldy].draw()
                self.lines[self.y].draw()
                print('\033[%i;%iH' % (self.top + self.y, self.left + self.innerleft + self.x - self.offx), end='')
            (oldy, oldx, oldmark) = (self.y, self.x, self.mark)
            if edited:
                edited = False
                if not modified:
                    modified = True
                    self.status('modified' + (' override' if override else ''))
            sys.stdout.flush()
            if stored is None:
                d = sys.stdin.read(1)
            else:
                d = stored
                stored = None
            if self.alerted:
                self.alert(None)
            if ord(d) == ord('@') - ord('@'):
                if self.mark is None:
                    self.mark = self.x
                    self.alert('Mark set')
                elif self.mark == ~(self.x):
                    self.mark = self.x
                    self.alert('Mark activated')
                elif self.mark == self.x:
                    self.mark = ~(self.x)
                    self.alert('Mark deactivated')
                else:
                    self.mark = self.x
                    self.alert('Mark set')
            elif ord(d) == ord('K') - ord('@'):
                if not self.lines[self.y].kill():
                    self.alert('At end')
                else:
                    edited = True
            elif ord(d) == ord('W') - ord('@'):
                if not self.lines[self.y].cut():
                    self.alert('No text is selected')
                else:
                    edited = True
            elif ord(d) == ord('Y') - ord('@'):
                if not self.lines[self.y].yank():
                    self.alert('Killring is empty')
                else:
                    edited = True
            elif ord(d) == ord('X') - ord('@'):
                self.alert('C-x')
                sys.stdout.flush()
                d = sys.stdin.read(1)
                self.alert(str(ord(d)))
                sys.stdout.flush()
                if ord(d) == ord('X') - ord('@'):
                    if self.lines[self.y].swap_mark():
                        self.alert('Mark swapped')
                    else:
                        self.alert('No mark is activated')
                elif ord(d) == ord('S') - ord('@'):
                    last = ''
                    for row in range(0, len(datalines)):
                        self.datamap[self.lines[row].name] = self.lines[row].text
                    saver()
                    modified = False
                    self.status('unmodified' + (' override' if override else ''))
                    self.alert('Saved')
                elif ord(d) == ord('C') - ord('@'):
                    break
                else:
                    stored = d
                    self.alert(None)
            elif (ord(d) == 127) or (ord(d) == 8):
                if not self.lines[self.y].erase():
                    self.alert('At beginning')
            elif ord(d) < ord(' '):
                if ord(d) == ord('P') - ord('@'):
                    if self.y == 0:
                        self.alert('At first line')
                    else:
                        self.y -= 1
                        self.mark = None
                        self.x = 0
                elif ord(d) == ord('N') - ord('@'):
                    if self.y < len(self.lines) - 1:
                        self.y += 1
                        self.mark = None
                        self.x = 0
                    else:
                        self.alert('At last line')
                elif ord(d) == ord('F') - ord('@'):
                    if not self.lines[self.y].move_point(1):
                        self.alert('At end')
                elif ord(d) == ord('E') - ord('@'):
                    if not self.lines[self.y].move_point(len(self.lines[self.y].text) - self.x):
                        self.alert('At end')
                elif ord(d) == ord('B') - ord('@'):
                    if not self.lines[self.y].move_point(-1):
                        self.alert('At beginning')
                elif ord(d) == ord('A') - ord('@'):
                    if not self.lines[self.y].move_point(-self.x):
                        self.alert('At beginning')
                elif ord(d) == ord('L') - ord('@'):
                    print('\033[H\033[2J', end='')
                    preredrawer()
                    for line in self.lines:
                        line.draw()
                    postredrawer()
                    self.realert()
                    self.restatus()
                elif ord(d) == ord('D') - ord('@'):
                    if not self.lines[self.y].delete():
                        self.alert('At end')
                    else:
                        edited = True
                elif d == '\033':
                    d = sys.stdin.read(1)
                    if d == '[':
                        d = sys.stdin.read(1)
                        if d == 'A':
                            stored = chr(ord('P') - ord('@'))
                        elif d == 'B':
                            if self.y == len(self.lines) - 1:
                                self.alert('At last line')
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
                                self.status(('modified' if modified else 'unmodified') + (' override' if override else ''))
                        elif d == '3':
                            d = sys.stdin.read(1)
                            if d == '~':
                                stored = chr(ord('D') - ord('@'))
                        elif d == '1':
                            d = sys.stdin.read(1)
                            if d == '~':
                                stored = chr(ord('A') - ord('@'))
                        elif d == '4':
                            d = sys.stdin.read(1)
                            if d == '~':
                                stored = chr(ord('E') - ord('@'))
                        else:
                            while True:
                                d = sys.stdin.read(1)
                                if (ord('a') <= ord(d)) and (ord(d) <= ord('z')): break
                                if (ord('A') <= ord(d)) and (ord(d) <= ord('Z')): break
                                if d == '~': break
                    elif d == 'O':
                        d = sys.stdin.read(1)
                        if d == 'H':
                            stored = chr(ord('A') - ord('@'))
                        elif d == 'F':
                            stored = chr(ord('E') - ord('@'))
                    elif (d == 'w') or (d == 'W'):
                        if not self.lines[self.y].copy():
                            self.alert('No text is selected')
                    elif (d == 'y') or (d == 'Y'):
                        if not self.lines[self.y].yank_cycle():
                            stored = chr(ord('Y') - ord('@'))
                elif d == '\n':
                    stored = chr(ord('N') - ord('@'))
            else:
                insert = d
                if len(insert) == 0:
                    continue
                if override:
                    self.lines[self.y].override(insert)
                else:
                    self.lines[self.y].insert(insert)
                edited = True


def phonysaver():
    pass
def phonypreredraw():
    pass
def phonypostredraw():
    pass
print('\033[H\033[2J')
old_stty = Popen('stty --save'.split(' '), stdout = PIPE).communicate()[0]
old_stty = old_stty.decode('utf-8', 'error')[:-1]
Popen('stty -icanon -echo -isig -ixon -ixoff'.split(' '), stdout = PIPE).communicate()
try:
    TextArea(['alpha', 'beta'], {'alpha' : 'a', 'beta' : 'be'}, 1, 1, 20, 4).run(phonysaver, phonypreredraw, phonypostredraw)
finally:
    print('\033[H\033[2J', end = '')
    sys.stdout.flush()
    Popen(['stty', old_stty], stdout = PIPE).communicate()

