'''
featherweight – A lightweight terminal news feed reader

Copyright © 2013, 2014  Mattias Andrée (maandree@member.fsf.org)

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


class Killring():
    '''
    Killring class
    '''
    
    def __init__(self, limit = 50):
        '''
        Constructor
        
        @param  limit:int  The maximum size of the killring
        '''
        self.killring, self.killmax, self.killptr = [], limit, 0
    
    
    def add(self, text):
        '''
        Add a text to the killring
        
        @param  text:str  The text to add
        '''
        self.killring.append(text)
        if len(self.killring) > self.killmax:
            self.killring[:] = self.killring[1:]
    
    
    def is_empty(self):
        '''
        Checks if the killring is empty
        
        @return  :bool  Whether the killring is empty
        '''
        return len(self.killring) == 0
    
    
    def reset(self):
        '''
        Resets the killring pointer
        '''
        self.killptr = len(self.killring) - 1
    
    
    def next(self):
        '''
        Get to the next item in the killring
        '''
        self.killptr -= 1
        if self.killptr < 0:
            self.killptr += len(self.killring)
    
    
    def get(self):
        '''
        Gets the current item in the killring
        
        @return  :str  The current item in the killring
        '''
        return self.killring[self.killptr]

