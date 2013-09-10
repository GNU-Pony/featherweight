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

