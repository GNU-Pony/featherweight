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



class Edit():
    '''
    A line edit
    '''
    
    def __init__(self, deleted, inserted, y, old_x, new_x):
        '''
        Constructor
        
        @param  deleted:str?   The text deleted by the edit
        @param  inserted:str?  The text inserted by the edit
        @param  y:int          The index of the line the edit was made one
        @param  old_x:int      The position on the line before the edit was made
        @param  new_x:int      The position on the line after the edit was made
        '''
        self.deleted, self.inserted = deleted, inserted
        self.y, self.old_x, self.new_x = y, old_x, new_x
    
    
    def reverse(self):
        '''
        Create a clone of the object but create a mirror object
        
        @return  :Edit  The object's opposite
        '''
        return Edit(self.inserted, self.deleted, self.y, self.new_x, self.new_y)



class Editring():
    '''
    Editing ring class
    '''
    
    def __init__(self, limit = 100):
        '''
        Constructor
        
        @param  limit:int  The maximum size of the ring
        '''
        self.editring, self.editmax, self.editptr, self.editdir = [], limit, 0, -1
    
    
    def is_empty(self):
        '''
        Checks if the editing is empty
        
        @return  :bool  Whether the editring is empty
        '''
        return len(self.editring) == 0
    
    
    def change_direction(self):
        '''
        Swap between undoing and redoing
        '''
        self.editdir = -(self.editdir)
    
    
    def push(self, edit):
        '''
        Insert a new edit to the editring
        
        @param  edit:Edit  The edit to insert
        '''
        self.editdir = -1
        self.editring[:] = self.editring[:self.editptr] + [edit] + self.editring[self.editptr:]
        if len(self.editring) > self.editmax:
            i = (self.editptr + self.editmax // 2) % self.editmax
            self.editring[:] = self.editring[:i] + self.editring[i + 1:]
    
    
    def pop(self):
        '''
        Get the next undo or redo
        
        @return  :(Edit, bool)?  The edit to preform (not reverse) and whether it is a undo
        '''
        if is_empty():
            return None
        if self.editptr < 0:
            self.editptr = min(1, len(self.editring))
            self.editdir = 1
        elif self.editptr == len(self.editring):
            self.editptr = max(1, len(self.editring) - 2)
            self.editdir = -1
        edit = self.editring[self.editptr]
        self.editptr += self.editdir
        return (edit, True) if self.editdir < 0 else (edit.reverse(), False)

