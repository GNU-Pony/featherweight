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
import pwd
import gettext
from subprocess import Popen, PIPE

gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
gettext.textdomain('@PKGNAME@')
_ = gettext.gettext



islinux = ('TERM' in os.environ) and (os.environ['TERM'] == 'linux')
'''
:bool  Running in Linux VT?  This is useful for selecting the best characters,
       as Linux VT has a limited character set.
'''

home = os.environ['HOME'] if 'HOME' in os.environ else None
'''
:str  The user's home directrory.
'''
if (home is None) or (len(home) == 0):
    home = pwd.getpwuid(os.getuid()).pw_dir

quote = (lambda x : _("'%s'") % x) if islinux else (lambda x : _('‘%s’') % x)
'''
Enclose a string in single-quotes

@param   x:str  The string
@return  :str   The string enclosed in quotes
'''

double_quote = (lambda x : _('"%s"') % x) if islinux else (lambda x : _('“%s”') % x)
'''
Enclose a string in double-quotes

@param   x:str  The string
@return  :str   The string enclosed in quotes
'''

abbr = lambda x : ('~%s' % x[len(home):] if x.startswith(home + '/') else x)
'''
Abbreviate a path

The replaces an the home directory with '~'

@param   x:str  The path
@return  :str   The path abbreviated

'''

root = '%s/.var/lib/%s' % (home, 'featherweight')
'''
:str  Where the program stores all data files
'''

terminated = False
'''
:bool  Exiting?
'''


def make_backup(filename):
    '''
    Backup a file and return its content
    
    @param   filename:str  The path of the file
    @return  :bytes        The content of the file
    '''
    backup = None
    if os.access(filename, os.F_OK):
        with open(filename, 'rb') as file:
            backup = file.read()
            with open(filename + '.bak', 'wb') as bakfile:
                bakfile.write(backup)
    return backup


def save_file(filename, backup, datafun):
    '''
    Save data to a file, but retry to restore it on failure
    
    @param  filename:str    The path of the file
    @param  backup:bytes?   The old content of the file
    @param  datafun:()→str  Nullary functional that evaluates to the new content
    '''
    # Store new data.
    try:
        with open(filename, 'wb') as file:
            file.write(datafun())
    except Exception as err:
	# Try to restore old file on error.
        try:
            if backup is not None:
                with open(filename, 'wb') as file:
                    file.write(backup)
        except:
            pass
        raise err


def save_file_or_die(filename, raise_error, datafun):
    '''
    Save data to a file, die verbosely on failure
    
    The error message assumes that there is a backup
    at `filename + '.bak'`
    
    @param  filename:str      The path of the file
    @param  raise_error:bool  Should an error be raised on error?
    @param  datafun:()→str    Nullary functional that evaluates to the new content
    '''
    global terminated, old_stty, root
    try:
        with open(filename, 'wb') as file:
            file.write(feed_info)
    except Exception as err:
        Popen(['stty', old_stty], stdout = PIPE, stderr = PIPE).communicate()
        print('\n\033[?9l\033[?25h\033[?1049l' if pid is None else '\n', end = '', flush = True)
        filename = abbr(root) + filename[len(root):]
        print('\033[01;31m%s\033[00m', _('Your %s was saved to %s.bak') % (filename, filename))
        terminated = True
        if raise_error:
            raise err

