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
import fcntl


def touch(file):
    '''
    Touch a lock file and return it opened
    
    @param   file:str  The file name of the lock
    @return  :ofile    The file handle
    '''
    file = open(file, 'a')
    file.flush()
    return file


def flock(file, exclusive, nonblocking = False):
    '''
    Apply file lock on a file
    
    @param  file:file         The file handle
    @param  exclusive:bool    Whether to use an exclusive lock, otherwise shared lock
    @param  nonblocking:bool  Whether to fail if an conflicting lock is already applied by a another process
    '''
    locktype = (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | (fcntl.LOCK_NB if nonblocking else 0)
    fcntl.flock(file.fileno(), locktype)


def unflock(file):
    '''
    Release file lock from a file
    
    @param  file:file  The file handle
    '''
    fcntl.flock(file.fileno(), fcntl.LOCK_UN)

