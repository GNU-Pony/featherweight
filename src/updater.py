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
import time
from subprocess import Popen, PIPE

from common import *
from flocker import *
from parser import *



def update_feed(feed, if_group, now = None):
    '''
    Update a feed and its subfeeds
    
    @param  feed:dict<str, _|int|itr<↑>>  The feed
    @param  if_group:str?                 The name of the group the feed should belong to
                                          for it to be updated, `None` to update everything
    @param  now:tuple(int)?               The current time, intended for internal use
    '''
    if now is None:
        now = time.gmtime()
        now = [now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec]
    if 'inner' in feed:
        if feed['group'] == if_group:
            if_group = None
        for feed in feed['inner']:
            update_feed(feed, if_group, now)
    elif ((if_group is None) or (feed['group'] == if_group)) and ('url' in feed) and (feed['url'] is not None):
        id = feed['id']
        with touch('%s/%s' % (root, id)) as feed_flock:
            flock(feed_flock, True)
            feed_info = None
            with open('%s/%s' % (root, id), 'rb') as file:
                feed_info = file.read().decode('utf-8', 'strict')
            feed_info = eval(feed_info) if len(feed_info) > 0 else {}
            if 'have' not in feed_info:
                feed_info['have'] = set()
            if 'unread' not in feed_info:
                feed_info['unread'] = set()
            if 'url' not in feed_info:
                feed_info['url'] = feed['url']
            have = feed_info['have']
            unread = feed_info['unread']
            url = feed_info['url']
            updated = True
            
            try:
                feed_data = None
                if url.startswith('file://'):
                    url = url[len('file://'):]
                    if os.access(url, os.F_OK):
                        with open(url, 'rb') as feed_file:
                            feed_data = feed_file.read().decode('utf-8', 'strict')
                else:
                    feed_data = Popen(['wget', url, '-O', '-'], stdout = PIPE).communicate()[0]
                feed_data = [] if feed_data is None else parse_feed(feed_data)
                old_data = []
                if os.access('%s/%s-content' % (root, id), os.F_OK):
                    with open('%s/%s-content' % (root, id), 'rb') as file:
                        bakdata = file.read()
                        with open('%s/%s-content.bak' % (root, id), 'wb') as bakfile:
                            bakfile.write(bakdata)
                    old_data = eval(bakdata.decode('utf-8', 'strict'))
                else:
                    bakdata = None
                for channel in feed_data:
                    for item in channel['items']:
                        if 'guid' not in item:
                            item['guid'] = item['link' if 'link' in item else 'title']
                        guid = item['guid']
                        if guid not in have:
                            unread.add(guid)
                            have.add(guid)
                            old_data.append(item)
                            if 'pubdate' not in item:
                                item['pubdate'] = now
                try:
                    with open('%s/%s-content' % (root, id), 'wb') as file:
                        file.write(repr(old_data).encode('utf-8'))
                except Exception as err:
                    try:
                        if bakdata is not None:
                            with open('%s/%s-content' % (root, id), 'wb') as bakfile:
                                bakfile.write(bakdata)
                    except:
                        pass
                    raise err
            except:
                updated = False
            
            if updated:
                if os.access('%s/%s' % (root, id), os.F_OK):
                    with open('%s/%s' % (root, id), 'rb') as file:
                        bakdata = file.read()
                        with open('%s/%s.bak' % (root, id), 'wb') as bakfile:
                            bakfile.write(bakdata)
                try:
                    with open('%s/%s' % (root, id), 'wb') as file:
                        file.write(repr(feed_info).encode('utf-8'))
                except Exception as err:
                    try:
                        with open('%s/%s' % (root, id), 'wb') as file:
                            file.write(bakdata)
                    except:
                        pass
                    raise err
                feed['new'] = len(unread)
            unflock(feed_flock)

