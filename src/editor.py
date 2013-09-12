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

import gettext
gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
gettext.textdomain('@PKGNAME@')
_ = gettext.gettext

from killring import *
from editring import *



INACTIVE_COLOUR = '34'
'''
:str?  The colour of an inactive line
'''

ACTIVE_COLOUR = '01;34'
'''
:str?  The colour of an active line
'''

SELECTED_COLOUR = '44;37'
'''
:str?  The colour of a selected text
'''

STATUS_COLOUR = '07'
'''
:str?  The colour of the status bar
'''

ALERT_COLOUR = None
'''
:str?  The colour of the alert message
'''


atleast = lambda x, minimum : (x is not None) and (x >= minimum)
'''
Test that a value is defined and of at least a minimum value
'''

limit = lambda x_min, x, x_max : min(max(x_min, x), x_max)
'''
Limit a value to a closed set
'''

ctrl = lambda key : chr(ord(key) ^ ord('@'))
'''
Return the symbol for a specific letter pressed in combination with Ctrl
'''

backspace = lambda x : (ord(x) == 127) or (ord(x) == 8)
'''
Check if a key stroke is a backspace key stroke
'''

class Jump():
    '''
    Create a cursor jump that can either be included in a print statement
    as a string or invoked
    
    @param   y:int         The row, 1 based
    @param   x:int         The column, 1 based
    @string  :str|()→void  Functor that can be treated as a string for jumping
    '''
    def __init__(self, y, x):
        self.string = '\033[%i;%iH' % (y, x)
    def __str__(self):
        return self.string
    def __call__(self):
        print(self.string, end = '')


## TODO  colours should be configurable with rc file
## TODO  ring limits should be configurable with rc file
## TODO  widthless characters should be ignored when calculating the size a text

## TODO  implement undo history
## 
##    Until the user has halted for 1 second (configurably) or has navigated using arrow keys or alternative key combinations,
##    edits should be accumulated and then stored in the editring. The edits is stored when the next keystroke is made, there
##    should not be a timer waits for the user to idle.
## 

class TextArea():
    '''
    GNU Emacs alike text area
    '''
    
    def __init__(self, fields, datamap, left = 1, top = 1, width = None, height = None):
        '''
        Constructor
        
        @param  fields:list<str>        Field names
        @param  datamap:dist<str, str>  Data map
        @param  left:int                Left position of the component, 1 based
        @param  top:int                 Top  position of the component, 1 based
        @param  width:int?              Width of the component,  `None` for screen width − left offset, negative for `None` plus that value
        @param  height:int?             Height of the component, `None` for screen height − top offset, negative for `None` plus that value
        '''
        if width  is None: width  = 0
        if height is None: height = 0
        if (width <= 0) or (height <= 0):
            screen_size = Popen('stty size'.split(' '), stdout = PIPE).communicate()[0].decode('utf-8', 'error')[:-1].split(' ')
            if width <= 0:   width  += int(screen_size[1]) - left + 1
            if height <= 0:  height += int(screen_size[0]) - top  + 1
        self.fields, self.datamap, self.left, self.top, self.width, self.height = fields, datamap, left, top, width - 1, height
        self.innerleft = len(max(self.fields, key = len)) + 3
        self.killring, self.editring = Killring(), Editring()
        data = lambda field : datamap[field] if field in datamap else ''
        self.lines = [TextArea.Line(self, self.fields[y], data(self.fields[y]), y) for y in range(len(self.fields))]
        self.areawidth = self.width - self.innerleft
        self.y, self.offy, self.x, self.offx, self.mark = 0, 0, 0, 0, None
        self.last_alert, self.last_status, self.alerted = None, None, False
    
    
    
    def initialise(self, initalise_terminal):
        '''
        Initialise terminal and TTY settings
        '''
        self.initalise_terminal = initalise_terminal
        if initalise_terminal:
            print('\033[?1049h', end='', flush=True)
        print('\033[H\033[2J', end='', flush=True)
        self.old_stty = Popen('stty --save'.split(' '), stdout = PIPE).communicate()[0]
        self.old_stty = self.old_stty.decode('utf-8', 'error')[:-1]
        Popen('stty -icanon -echo -isig -ixon -ixoff'.split(' '), stdout = PIPE).communicate()
    
    def close(self):
        '''
        Restore the terminal to the state before `initialise` as invoked
        '''
        sys.stdout.flush()
        Popen(['stty', self.old_stty], stdout = PIPE).communicate()
        print('\033[H\033[2J', end='', flush=True)
        if self.initalise_terminal:
            print('\033[?1049l', end='', flush=True)
    
    
    
    def get_selection(self, for_display = False):
        '''
        Get the selected texts start and end on the X-axis
        
        @param  for_display:bool         Whether to translate to screen position rather than, excluding the left inset
        @param  (start, end):(int, int)  The start and end
        '''
        a = min(self.mark, self.x)
        b = max(self.mark, self.x)
        if for_display:
            a = limit(0, a - self.offx, self.areawidth)
            b = limit(0, b - self.offx, self.areawidth)
        return (a, b)
    
    
    class Line():
        '''
        A line in the text area
        '''
        
        def __init__(self, area, name, text, y):
            '''
            Constructor
            
            @param  area:TextArea  The text area
            @param  name:str       The name of the, displayed at the left side
            @param  text:str       The text in the line
            @param  y:int          The y position of the line
            
            '''
            self.area, self.name, self.text, self.y = area, name, text, y
            self.killring = self.area.killring
            self.jump = lambda x : Jump(self.area.top + self.y - self.area.offy, self.area.left + self.area.innerleft + x)
        
        
        def is_active(self):
            '''
            Checks if the line is the focused line
            
            @return  :bool  Whether the line is the focused line
            '''
            return self.area.y == self.y
        
        
        def has_selection(self):
            '''
            Checks if there is any text selected, assuming the line is focused
            
            @param  :bool  Whether there is any text selected
            '''
            return atleast(self.area.mark, 0) and (self.area.mark != self.area.x)
        
        
        def draw(self):
            '''
            Redraw the line
            '''
            if 0 <= self.y - self.area.offy < self.area.height - 2:
                leftside = ACTIVE_COLOUR if self.is_active() else INACTIVE_COLOUR
                if leftside is not None:
                    leftside = '%s\033[%sm%s:\033[00m' % (self.jump(-(self.area.innerleft)), leftside, self.name)
                else:
                    leftside = '%s%s:' % (self.jump(-(self.area.innerleft)), self.name)
                text = (self.text[self.area.offx if self.is_active() else 0:] + ' ' * self.area.areawidth)[:self.area.areawidth]
                if self.is_active() and atleast(self.area.mark, 0):
                    (a, b) = self.area.get_selection(True)
                    if a != b:
                        if SELECTED_COLOUR is not None:
                            text = text[:a] + ('\033[%sm%s\033[00m' % (SELECTED_COLOUR, text[a : b])) + text[b:]
                print('%s%s%s' % (leftside, self.jump(0), text), end='')
                if self.is_active():
                    self.jump(self.area.x - self.area.offx)()
        
        
        def copy(self):
            '''
            Copy the selected text
            
            @return  :bool  Whether any text select, and therefore copied
            '''
            if self.has_selection():
                (a, b) = self.area.get_selection()
                self.killring.add(self.text[a : b])
                (a, b) = self.area.get_selection(True)
                text = self.text[self.area.offx:][:self.area.areawidth][a : b]
                print('%s%s' % (self.jump(a), text), end='')
                self.area.mark = None
                return True
            return False
        
        
        def cut(self):
            '''
            Cut the selected text
            
            @return  :bool  Whether any text select, and therefore cut
            '''
            mark, x = self.area.mark, self.area.x
            if self.copy():
                self.area.mark, self.area.x = mark, x
                self.delete()
                return True
            return False
        
        
        def kill(self):
            '''
            Cut all text on the same line after the position of the point
            
            @return  :bool  Whether the point was not at the end of the line, and therefore a cut was made
            '''
            if self.area.x < len(self.text):
                self.area.mark = len(self.text)
                self.cut()
                return True
            return False
        
        
        def delete(self):
            '''
            Delete the selected text or, if none, the character at the position of the point
            
            @return  :bool  The point was not at the end of the line or something was selected, and therefore a deletion was made
            '''
            removed = 0
            if self.has_selection():
                (a, b) = self.area.get_selection()
                self.text = self.text[:a] + self.text[b:]
                self.area.x = a
                if self.area.offx > len(self.text):
                    self.area.offx = max(len(self.text) - self.area.areawidth, 0)
                    self.area.mark = None
                    print('%s%s' % (self.jump(0), ' ' * self.area.areawidth), end='')
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
            a = limit(0, self.area.x - self.area.offx, self.area.areawidth)
            print('%s%s%s' % (self.jump(a), text[a:] + ' ' * removed, self.jump(a)), end='')
            return True
        
        
        def erase(self):
            '''
            Select the selected text or the character directly before the position of the point
            
            @return  :bool  Whether point as at the beginning of the line or any text was selected, and therefore an erasure was made
            '''
            if not self.has_selection():
                self.area.mark = None
                if self.area.x == 0:
                    return False
                self.area.x -= 1
                if self.area.x < self.area.offx:
                    self.area.offx = max(self.area.offx - self.area.areawidth, 0)
                    self.draw()
                    self.jump(self.area.x - self.area.offx)()
            self.delete()
            return True
        
        
        def yank(self):
            '''
            Yank the text from the top of the killring
            
            @return  :bool  Whether the killring was not empty, and therefor a yank was made
            '''
            if self.killring.is_empty():
                return False
            self.area.mark = None
            yanked = self.killring.get()
            self.text = self.text[:self.area.x] + yanked + self.text[self.area.x:]
            self.area.x += len(yanked)
            if self.area.x > self.area.offx + self.area.areawidth:
                self.area.offx = len(self.text) - self.area.areawidth
            print('%s%s' % (self.jump(0), ' ' * self.area.areawidth), end='')
            self.draw()
            self.jump(self.area.x - self.area.offx)()
            return True
        
        
        def yank_cycle(self):
            '''
            Replace the recently yank text with the next in the killring
            
            @return  :bool  False on failure, which happens if the killring is empty or if the text before the point is not the yanked text
            '''
            if self.killring.is_empty():
                return False
            yanked = self.killring.get()
            if self.text[max(self.area.x - len(yanked), 0) : self.area.x] != yanked:
                return False
            self.area.mark = self.area.x - len(yanked)
            self.delete()
            self.killring.next()
            self.yank()
            return True
        
        
        def move_point(self, delta):
            '''
            Move the the point
            
            @param   delta:int  The number of steps to move the point to the right
            @return  :bool      Whether the point has been moved
            '''
            x = self.area.x + delta
            if 0 <= x <= len(self.text):
                self.area.x = x
                if delta < 0:
                    if self.area.offx > self.area.x:
                        self.area.offx = max(self.area.x - 3 * self.area.areawidth // 4, 0)
                        self.draw()
                    else:
                        print('\033[%iD' % -delta, end='')
                elif delta > 0:
                    if self.area.x - self.area.offx > self.area.areawidth:
                        self.area.offx = self.area.x - self.area.areawidth // 4
                        self.draw()
                    else:
                        print('\033[%iC' % delta, end='')
                return delta != 0
            return False
        
        
        def swap_mark(self):
            '''
            Swap the position of the mark and the position of the point
            
            @return  :bool  Whether the mark was set, and therefore as swap was made
            '''
            if atleast(self.area.mark, 0):
                self.area.mark, self.area.x = self.area.x, self.area.mark
                return True
            return False
        
        
        def override(self, insert, override = True):
            '''
            Insert a text (by default) by overriding the existing text at the position of the point
            
            @param  insert:str     The text to insert
            @param  override:bool  Whether to override
            '''
            if atleast(self.area.mark, 0):
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
                    print('%s\033[%iP' % (self.jump(self.area.areawidth - len(insert)), len(insert)), end='')
                    print('%s\033[%i@' % (self.jump(oldx - self.area.offx), len(insert)), end='')
                print(insert, end='')
            else:
                self.area.offx = self.area.x - self.area.areawidth // 4
                self.jump(0)()
                print(' ' * self.area.areawidth, end='')
                self.draw()
        
        
        def insert(self, insert):
            '''
            Insert a text at the position of the point
            
            @param  insert:str  The text to insert
            '''
            self.override(insert, False)
    
    
    
    def limit_text(self, text):
        max_len = self.width
        if len(text) > max_len:
            text = text[:max_len - 1] + '…'
        return text
    
    def status(self, text):
        '''
        Print a message to the status bar
        
        @param  text:str  The message
        '''
        txt = ' (' + text + ') '
        y = self.top + self.y - self.offy
        x = self.left + self.innerleft + self.x - self.offx
        dashes = max(self.width - len(txt), 0)
        Jump(self.top + self.height - 2, self.left)()
        if STATUS_COLOUR is not None:
            print('\033[%sm%s-\033[00m%s' % (STATUS_COLOUR, self.limit_text(txt + '-' * dashes), Jump(y, x)), end='')
        else:
            print('%s-%s' % (self.limit_text(txt + '-' * dashes), Jump(y, x)), end='')
        self.last_status = text
    
    def alert(self, text):
        '''
        Print a message to the alert bar
        
        @param  text:str  The message
        '''
        if text is None:
            self.alert('')
            self.alerted = False
        else:
            y = self.top + self.y - self.offy
            x = self.left + self.innerleft + self.x - self.offx
            Jump(self.top + self.height - 1, self.left)()
            if ALERT_COLOUR is not None:
                print('\033[2K\033[%sm%s\033[00m%s' % (ALERT_COLOUR, self.limit_text(text), Jump(y, x)), end='')
            else:
                print('\033[2K%s%s' % (self.limit_text(text), Jump(y, x)), end='')
            self.alerted = True
        self.last_alert = text
    
    def restatus(self):
        '''
        Reprint the status bar
        '''
        self.status(self.last_status)
    
    def realert(self):
        '''
        Reprint the alert bar
        '''
        self.alert(self.last_alert)
    
    
    def run(self, saver, preredrawer = None, postredrawer = None):
        '''
        Execute text reading
        
        @param  saver:()→bool          Save method
        @param  preredrawer:()?→void   Method to call before redrawing screen
        @param  postredrawer:()?→void  Method to call after  redrawing screen
        '''
        modified = False
        override = False
        
        oldy, oldx, oldmark = self.y, self.x, self.mark
        stored = ctrl('L')
        edited = False
        
        def redraw():
            print('\033[H\033[2J', end='')
            if preredrawer is not None:
                preredrawer()
            for line in self.lines:
                line.draw()
            if postredrawer is not None:
                postredrawer()
            self.realert()
            self.restatus()
        
        def store(key, value_map, required_next = None):
            nonlocal stored
            if key in value_map:
                if required_next is not None:
                    if sys.stdin.read(1) != required_next:
                        return False
                stored = value_map[key]
                return True
            return False
        
        def edit(method, error_message):
            nonlocal edited
            if not method(self.lines[self.y]):
                self.alert(error_message)
            else:
                edited = True
        
        def move_point(delta_x, error_message):
            if not self.lines[self.y].move_point(delta_x):
                self.alert(error_message)
        
        def update_status():
            below = len(self.lines) - (self.offy + self.height - 2)
            mode_text = _('modified' if modified else 'unmodified')
            ins_text = (' ' + _('override')) if override else ''
            above = ' +%i↑' % self.offy if self.offy > 0 else ''
            below = ' +%i↓' % below if below > 0 else ''
            self.status(mode_text + ins_text + above + below)
        
        def ensure_y():
            nonlocal stored
            if self.y < self.offy:
                self.offy = self.y
            if self.y - self.offy > self.height - 3:
                self.offy = self.y - self.height + 3
            update_status()
            redraw()
        
        def letter_type(char):
            return char == ' '
        
        update_status()
        while True:
            if atleast(oldmark, 0) or atleast(self.mark, 0):
                self.lines[self.y].draw()
            if self.y != oldy:
                self.lines[oldy].draw()
                self.lines[self.y].draw()
            oldy, oldx, oldmark = self.y, self.x, self.mark
            if edited:
                edited = False
                if not modified:
                    modified = True
                    update_status()
            sys.stdout.flush()
            d = sys.stdin.read(1) if stored is None else stored
            stored = None
            if self.alerted:
                self.alert(None)
            if d == -1: # page up
                if self.y == 0:
                    self.alert(_('At first line'))
                elif self.y == self.offy:
                    self.offy -= self.height - 2
                    self.offy = max(0, self.offy)
                    self.y = self.offy
                    update_status()
                    redraw()
                    self.mark, self.x, self.offx = None, 0, 0
                else:
                    self.y = self.offy
                    self.mark, self.x, self.offx = None, 0, 0
            elif d == -2: # page down
                if self.y == len(self.lines) - 1:
                    self.alert(_('At last line'))
                elif self.y == self.offy + self.height - 3:
                    self.y += self.height - 2
                    self.y = min(self.y, len(self.lines) - 1)
                    self.offy = max(0, self.y - self.height + 3)
                    update_status()
                    redraw()
                    self.mark, self.x, self.offx = None, 0, 0
                else:
                    self.y = self.offy + self.height - 3
                    self.mark, self.x, self.offx = None, 0, 0
            elif d == -3:
                if self.x == 0:  self.alert(_('At beginning'))
                else:
                    x = self.x
                    text = self.lines[self.y].text
                    t = letter_type(text[x - 1])
                    while (x > 0) and (letter_type(text[x - 1]) == t):
                        x -= 1
                    self.lines[self.y].move_point(x - self.x)
            elif d == -4:
                if self.x == len(self.lines[self.y].text):  self.alert(_('At end'))
                else:
                    x = self.x
                    text = self.lines[self.y].text
                    t = letter_type(text[x])
                    while (x < len(text)) and (letter_type(text[x]) == t):
                        x += 1
                    self.lines[self.y].move_point(x - self.x)
            elif d == ctrl('@'):
                if   self.mark is None:       self.mark = self.x    ; self.alert(_('Mark set'))
                elif self.mark == ~(self.x):  self.mark = self.x    ; self.alert(_('Mark activated'))
                elif self.mark == self.x:     self.mark = ~(self.x) ; self.alert(_('Mark deactivated'))
                else:                         self.mark = self.x    ; self.alert(_('Mark set'))
            elif backspace(d):    edit(lambda L : L.erase(), _('At beginning'))
            elif d == ctrl('K'):  edit(lambda L : L.kill(),  _('At end'))
            elif d == ctrl('W'):  edit(lambda L : L.cut(),   _('No text is selected'))
            elif d == ctrl('Y'):  edit(lambda L : L.yank(),  _('Killring is empty'))
            elif d == ctrl('R'):  self.editring.change_direction()
            elif d in (ctrl('_'), ctrl('U')):
                if self.editring.is_empty():
                    self.alert(_('Nothing to undo'))
                else:
                    (edit, undo) = self.editring.pop()
                    self.alert(_('Undo!' if undo else 'Redo!'))
                    fix_offx = not (self.offx <= edit.x < self.offx + self.areawidth)
                    text = self.lines[edit.y]
                    if edit.deleted is not None:
                        a, b = max(edit.old_x, edit.new_x), min(edit.old_x, edit.new_x)
                        text = text[:a] + text[b:]
                    if edit.inserted is not None:
                        text = text[:edit.old_x] + edit.inserted + text[edit.old_x:]
                    self.lines[edit.x] = text
                    self.x = edit.new_x
                    if self.y != edit.y:
                        self.mark = None
                        fix_offx = True
                        self.y = edit.y
                    if fix_offx:
                        self.offx = max(edit.x - self.areawidth + 1, 0)
                        self.lines[self.y].draw()
                    if not (self.offy <= edit.y < self.offy + self.height - 2):
                        ensure_y()
            elif d == ctrl('X'):
                self.alert('C-x')
                sys.stdout.flush()
                d = sys.stdin.read(1)
                self.alert(str(ord(d)))
                sys.stdout.flush()
                if d == ctrl('X'):
                    self.alert(_('Mark swapped' if self.lines[self.y].swap_mark() else 'No mark is activated'))
                elif d == ctrl('S'):
                    last = ''
                    for row in range(0, len(self.lines)):
                        self.datamap[self.lines[row].name] = self.lines[row].text
                    if saver():
                        modified = False
                        update_status()
                        self.alert(_('Saved'))
                    else:
                        self.alert(_('Failed to save!'))
                elif d == ctrl('C'):
                    break
                else:
                    stored = d
                    self.alert(None)
            elif ord(d) < ord(' '):
                if d == ctrl('P'):
                    if self.y == 0:
                        self.alert(_('At first line'))
                    else:
                        self.y -= 1
                        ensure_y()
                        self.mark, self.x, self.offx = None, 0, 0
                        update_status()
                elif d == ctrl('N'):
                    if self.y == len(self.lines) - 1:
                        self.alert(_('At last line'))
                    else:
                        self.y += 1
                        ensure_y()
                        self.mark, self.x, self.offx = None, 0, 0
                        update_status()
                elif d == ctrl('D'):  edit(lambda L : L.delete(), _('At end'))
                elif d == ctrl('F'):  move_point(1, _('At end'))
                elif d == ctrl('E'):  move_point(len(self.lines[self.y].text) - self.x, _('At end'))
                elif d == ctrl('B'):  move_point(-1, _('At beginning'))
                elif d == ctrl('A'):  move_point(-(self.x), _('At beginning'))
                elif d == ctrl('L'):  redraw()
                elif d == '\033':
                    d = sys.stdin.read(1)
                    if d == '[':
                        d = sys.stdin.read(1)
                        if store(d, {'C':ctrl('F'), 'D':ctrl('B'), 'A':ctrl('P'), 'B':ctrl('N')}): pass
                        elif store(d, {'3':ctrl('D'), '4':ctrl('E'), '5':-1, '6':-2}, '~'): pass
                        elif d == '1':
                            d = sys.stdin.read(1)
                            if d == '~':  stored = ctrl('A')
                            elif d == ';':
                                d = sys.stdin.read(1)
                                if d == '5':    store(sys.stdin.read(1), {'C':-4, 'D':-3, 'A':-1, 'B':-2}) # ctrl
                                elif d == '2': # shift
                                    store(sys.stdin.read(1), {'C':ctrl('F'), 'D':ctrl('B')})
                                    if stored is not None:
                                        if not atleast(self.mark, 0):
                                            self.alert(_('Mark set'))
                                            self.mark = self.x
                                        if stored == ctrl('F'):  move_point(1, _('At end'))
                                        else:                    move_point(-1, _('At beginning'))
                                        stored = None
                        elif d == '2':
                            if sys.stdin.read(1) == '~':
                                override = not override
                                update_status()
                        else:
                            while True:
                                d = sys.stdin.read(1)
                                if ord('a') <= ord(d.lower()) <= ord('z'): break
                                if d == '~': break
                    elif d == 'O':
                        store(sys.stdin.read(1), {'H':ctrl('A'), 'F':ctrl('E')})
                    elif store(d, {'P':-1, 'p':-1, 'N':-2, 'n':-2, 'B':-3, 'b':-3, 'F':-4, 'f':-4}): pass
                    elif d.lower() == 'w':
                        if not self.lines[self.y].copy():
                            self.alert(_('No text is selected'))
                    elif d.lower() == 'y':
                        if not self.lines[self.y].yank_cycle():
                            stored = ctrl('Y')
                        else:
                            edited = True
                elif d == '\n':
                    stored = ctrl('N')
            else:
                insert = d
                if len(insert) == 0:
                    continue
                if override:  self.lines[self.y].override(insert)
                else:         self.lines[self.y].insert(insert)
                edited = True


if __name__ == '__main__': # For testing
    def phonysaver():
        return True
    area = None
    try:
        area = TextArea(('a be se de e eff ge hå i ji kå ell emm enn o pe ku ärr ess te u ve dubbel-ve eks y säta å ä ö').split(' '), {}, 6, 4, 40, 10)
        area.initialise(True)
        area.run(phonysaver)
    finally:
        if area is not None:
            area.close()

