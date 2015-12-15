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

### Vast array storage technique. ###



class Vast:
    def __init__(self, pathname, writeable = False):
        '''
        Constructor.
        
        @param  pathname:str    The pathname of the file to use.
        @param  writeable:bool  Should be file be open for writting too?
        '''
        INTSIZE = 20
        
        self.pathname = pathname
        self.fd = os.open(pathname, os.O_RDWR if writeable else os.O_RDONLY)
        try:
            os.posix_fadvise(self.fd, 0, 0, os.POSIX_FADV_RANDOM)
        except:
            pass
        self.width    = int(self.__read(INTSIZE, INTSIZE * 0).decode('utf-8', 'strict'))
        self.items    = int(self.__read(INTSIZE, INTSIZE * 1).decode('utf-8', 'strict'))
        self.size     = int(self.__read(INTSIZE, INTSIZE * 2).decode('utf-8', 'strict'))
        self.removed  = int(self.__read(INTSIZE, INTSIZE * 3).decode('utf-8', 'strict'))
        self.offset = INTSIZE * 4
        self.xwidth = self.width + INTSIZE * 2
    
    
    def __del__(self):
        '''
        Destructor.
        '''
        os.close(self.fd)
    
    
    def __read(self, length, offset):
        '''
        Wrapper around `os.pread` to reads as much as
        requested, from the opened file.
        
        @param   length:int  The number of bytes to read.
        @param   offset:int  Whence shall we read?
        @return  :bytes      The requested area of the file.
        '''
        rc = []
        while True:
            got = os.pread(self.fd, length, offset)
            if len(got) == 0:
                break
            rc += got
            length -= len(got)
            offset += len(got)
        return rc
    
    
    def __write(self, buf, offset):
        '''
        Wrapper around `os.pwrite` to writes as much as
        requested, to the opened file.
        
        @param  buf:bytes   The data to write.
        @param  offset:int  Whence shall we write?
        '''
        while len(buf) > 0:
            wrote = os.pwrite(self.fd, buf, offset)
            offset += wrote
            buf = buf[wrote:]
    
    
    def __compare_key(self, a, b):
        '''
        Compare to keys.
        
        `a` and `b` must not end with the same byte.
        Their length must be exactly `self.width`.
        
        @param  a:bytes  Left comparand.
        @param  b:bytes  Right comparand.
        '''
        i = 0
        while a[i] == b[i]:
            i += 1
        return 0 if (i == self.width) else (a[i] - b[i])
    
    
    def __find(self, key):
        '''
        Search for an entry.
        
        @param   key:str                          The key.
        @return  :(pos:int, off:int? , len:int?)  The positing of the key in the entry list,
                                                  or where it should be inserted if `off` is `None`;
                                                  Where in the file the data for the key begin,
                                                  `None` if the key was not found; and
                                                  the number of bytes the data of the key consists,
                                                  `None` if `off` is `None`, zero if the entry has
                                                  been removed.
        '''
        key = bytes(reversed(key.encode('utf-8')))
        # The keys are reversed to reduce the risk that
        # the beginning of the keys are identical, and thereby
        # reduce the time spent in `__compare_key`.
        key += bytes([0] * (self.width - len(key) - 1) + [1])
        # The 1 at the end is so that `__compare_key` always end
        # at then end (it is a zero in the if file).
        
        imin, imax = 0, self.items - 1
        while imin <= imax:
            imid = (imin + imax) // 2 # Python uses bignum.
            entry = self.__read(self.xwidth, self.offset + imid * self.xwidth)
            c = self.__compare_key(entry, key)
            if c < 0:
                imin = imid + 1
            else if c > 0:
                imax = imid - 1
            else:
                break
        
        if imin > imax:
            return (imin, None, None)
        
        entry = entry[:self.width].decode('utf-8', 'strict')
        offset = int(entry[:len(entry) // 2])
        length = int(entry[len(entry) // 2:])
        
        return (imin, offset, length)
    
    
    def lookup(self, key):
        '''
        Lookup an entry in the file.
        
        @param   key:str      The key.
        @return  ¿?|None|...  `None` if there is no such entry, `...` if it has been removed,
                              otherwise, the stored value parsed with `eval`.
        '''
        (_index, offset, length) = self.__find(key)
        if offset is None:
            return None
        if length == 0:
            return ...
        return eval(self.__read(length, offset).decode('utf-8', 'strict'))
    
    
    def tidy(self):
        '''
        Remove dead space.
        '''
        INTSIZE = (self.xwidth - self.width) // 2
        entries = []
        data = []
        
        # Fetch content, and update pointers without saving to the file yet.
        ptr = self.offset + self.size * self.xwidth
        for i in range(self.items):
            entry = self.__read(self.xwidth - self.width, self.offset + i * self.xwidth + self.width)
            entry = entry.decode('utf-8', 'strict')
            offset = int(entry[:len(entry) // 2])
            length = int(entry[len(entry) // 2:])
            if length > 0:
                data.append(self.__read(length, offset))
            entries.append((ptr if length > 0 else 0, length))
            ptr += length
        
        # Update stored content.
        ptr = self.offset + self.size * self.xwidth
        for datum in range(data):
            entry = self.__write(datum, ptr)
            ptr += len(datum)
        os.ftruncate(self.fd, ptr)
        
        # Update all pointers in the entry list.
        for (ptr, length) in range(self.items):
            entry = ('%0*i%0*i' % (INTSIZE, ptr, INTSIZE, length)).encode('utf-8')
            self.__write(entry, self.offset + i * self.xwidth + self.width)
    
    
    def remove(self, key):
        '''
        Remove an entry.
        
        @param  key:str  The key of the entry.
        '''
        INTSIZE = (self.xwidth - self.width) // 2
        
        # Get entry, and update dead space counter.
        (index, offset, length) = self.__find(key)
        self.removed += length
        
        # Store dead space counter to file, and mark entries as removed.
        self.__write(('%0*i' % (INTSIZE, self.removed)).encode('utf-8'), INTSIZE * 3)
        self.__write(('0' * (2 * INTSIZE)).encode('utf-8'), self.offset + index * self.xwidth + self.width)
        
        # More than 1MB dead space? Remove dead space.
        if self.removed >= 1 << 20:
            self.tidy()
    
    
    def update(self):
        pass # TODO
    
    
    def add(self, softtable = True):
        pass # TODO
    
    
    def sort_table(self):
        pass # TODO

