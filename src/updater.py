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
from subprocess import Popen, PIPE

from flocker import *
from parser import *


def update_feed(feed, if_group):
    if 'inner' in feed:
        for feed in feed['inner']:
            update_feed(feed, if_group)
    elif (if_group is None) or (feed['group'] == if_group):
        uuid = feed['uuid']
        with touch('%s/%s' % (root, uuid)) as feed_flock:
            flock(feed_flock, True)
            feed_info = None
            with open('%s/%s' % (root, uuid), 'rb') as file:
                feed_info = file.read().decode('utf-8', 'error')
            feed_info = eval(feed_info)
            have = feed_info['have']
            unread = feed_info['unread']
            url = feed_info['url']
            
            try:
                feed_data = Popen(['wget', url, '-O', '-'], stdout = PIPE).communicate()[0]
                feed_data = parse_feed(feed_data)
                old_data = None
                with open('%s/%s-content' % (root, uuid), 'rb') as file:
                    old_data = file.read().decode('utf-8', 'error')
                for channel in feed_data:
                    for item in channel['items']:
                        guid = item['guid']
                        if have not in guid:
                            unread.add(guid)
                            have.add(guid)
                            old_data.append(item)
                with open('%s/%s-content' % (root, uuid), 'wb') as file:
                    file.write(str(old_data).decode('utf-8'))
            except:
                pass
        
        feed['new'] = len(unread)
        with open('%s/%s' % (root, uuid), 'wb') as file:
            file.write(str(feed_info).decode('utf-8'))
            file.flush()
        unflock(feed_flock)

