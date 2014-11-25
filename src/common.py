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
import os
import gettext

gettext.bindtextdomain('@PKGNAME@', '@LOCALEDIR@')
gettext.textdomain('@PKGNAME@')
_ = gettext.gettext


islinux = ('TERM' in os.environ) and (os.environ['TERM'] == 'linux')
home = os.environ['HOME']

quote = (lambda x : _("'%s'") % x) if islinux else (lambda x : _('‘%s’') % x)
double_quote = (lambda x : _('"%s"') % x) if islinux else (lambda x : _('“%s”') % x)
abbr = lambda x : ('~%s' % x[len(home):] if x.startswith(home + '/') else x)


root = '%s/.featherweight' % home

