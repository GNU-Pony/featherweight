'''
featherweight – A lightweight terminal news feed reader

Copyright © 2013, 2014, 2015  Mattias Andrée (maandree@member.fsf.org)

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
import fcntl

### File locking, so we can have multiple processes running. ###


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
    
    @param  file:file             The file handle
    @param  exclusive:bool        Whether to use an exclusive lock, otherwise shared lock
    @param  nonblocking:bool|str  Whether to fail if an conflicting lock is already applied,
                                  by a another process, or if a string, the message to print
                                  if the file is already locked
    '''
    if isinstance(nonblocking, bool):
        locktype = (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | (fcntl.LOCK_NB if nonblocking else 0)
        fcntl.flock(file.fileno(), locktype)
    else:
        try:
            flock(file, exclusive, True)
        except:
            print(nonblocking)
            flock(file, exclusive)


def unflock(file):
    '''
    Release file lock from a file
    
    @param  file:file  The file handle
    '''
    fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def flock_fork(file):
    '''
    Attempt to apply an exlusive file lock on a file,
    if it is blocking, fork the process and wait
    until it does not block anymore
    
    Stop what you are doing if zero is returned
    
    @param   file:file  The file handle
    @return  :int?      `None` if there as no fork, otherwise the rules of `os.fork`
    '''
    pid = None
    try:
        flock(file, True, True)
    except:
        pid = os.fork()
    if (pid is not None) and (not pid == 0):
        flock(feed_flock, True)
    return pid


def unflock_fork(file, pid):
    '''
    Take appropriate actions when finished with the file lock,
    this may exit the program
    
    Do not call if `flock_fork` returned zero
    
    @param  file:file  The file handle
    @param  :int?      The return of `flock_fork`
    '''
    unflock(file)
    if pid is not None:
        sys.exit(0)

