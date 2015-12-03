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

