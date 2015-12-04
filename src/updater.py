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
import time
from subprocess import Popen, PIPE

from common import *
from flocker import *
from parser import *



def fetch_file(url):
    '''
    Fetches a files, local or remote
    
    @param   url:str  The URL of the file
    @retrun  :str     The content of the file
    '''
    data = None
    if url.startswith('file://'):
        url = url[len('file://'):]
        if os.access(url, os.F_OK):
            with open(url, 'rb') as file:
                data = file.read().decode('utf-8', 'strict')
    else:
        data = Popen(['wget', url, '-O', '-'], stdout = PIPE).communicate()[0]
    return data


def update_feed(feed, if_group, now = None):
    '''
    Update a feed and its subfeeds
    
    @param  feed:dict<str, _|int|itr<↑>>  The feed
    @param  if_group:str?                 The name of the group the feed should belong to
                                          for it to be updated, `None` to update everything
    @param  now:tuple(int)?               The current time, intended for internal use
    '''
    # Get the current time.
    if now is None:
        now = time.gmtime()
        now = [now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec]
    
    # Update node.
    if 'inner' in feed:
        # This is a branch.
        
        # If the node is in the group, all its children are too.
        if feed['group'] == if_group:
            if_group = None
        
        # Update all children.
        for feed in feed['inner']:
            update_feed(feed, if_group, now)
        
    elif ((if_group is None) or (feed['group'] == if_group)) and ('url' in feed) and (feed['url'] is not None):
        # This is a leaf, it has an url, and is no the selected group.
        
        # Get the ID if the node.
        id = feed['id']
        
        # Get pathnames.
        metafile = '%s/%s' % (root, id)
        datafile = '%s/%s-content' % (root, id)
        
        # Acquire feed...
        with touch(metafile) as feed_flock:
            # ... and update.
            
            # Lock the feed file for writing.
            flock(feed_flock, True)
            
            # Load feed metadata.
            feed_info = None
            with open(metafile, 'rb') as file:
                feed_info = file.read().decode('utf-8', 'strict')
            feed_info = eval(feed_info) if len(feed_info) > 0 else {}
            
            # Default missing metadata.
            if 'have' not in feed_info:
                feed_info['have'] = set()
            if 'unread' not in feed_info:
                feed_info['unread'] = set()
            if 'url' not in feed_info:
                feed_info['url'] = feed['url']
            
            # Fetch metadata.
            have = feed_info['have']
            unread = feed_info['unread']
            url = feed_info['url']
            updated = True
            
            # Update content.
            try:
                # Fetch feed.
                feed_data = fetch_file(url)
                feed_data = [] if feed_data is None else parse_feed(feed_data)
                
                # Create backup, and parse content.
                bakdata = make_backup(datafile)
                content = [] if bakdata is None else eval(bakdata.decode('utf-8', 'strict'))
                
                # Find new articles.
                for channel in feed_data:
                    for item in channel['items']:
                        if 'guid' not in item:
                            # Default GUID to the link, if missing.
                            item['guid'] = item['link' if 'link' in item else 'title']
                        guid = item['guid']
                        if guid not in have:
                            # Article is new, remember that/it.
                            unread.add(guid)
                            have.add(guid)
                            content.append(item)
                            # Default publication time to retrieval, if missing.
                            if 'pubdate' not in item:
                                item['pubdate'] = now
                
                # Update content file.
                save_file(datafile, bakdata, lambda : repr(content).encode('utf-8'))
            except:
                updated = False
            
            # Update metadata.
            if updated:
                # Update metadata file.
                bakdata = make_backup(metafile)
                save_file(metafile, bakdata, lambda : repr(feed_info).encode('utf-8'));
                # Update new-articles counter.
                feed['new'] = len(unread)
            
            # Release lock over file, we are done here.
            unflock(feed_flock)

