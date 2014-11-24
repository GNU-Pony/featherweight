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
import sys
from subprocess import Popen, PIPE

from common import *
from common import _
from flocker import *
from trees import *
from editor import *


MONTHS = { 1 : 'January',
           2 : 'February',
           3 : 'Marsh',
           4 : 'April',
           5 : 'May',
           6 : 'June',
           7 : 'July',
           8 : 'August',
           9 : 'September',
          10 : 'October',
          11 : 'November',
          12 : 'December'}



def open_feed(feed_node):
    '''
    Inspect a feed
    
    @param   feed_node:dict<str, _|str>  The node in the feed tree we the feed we are inspecting
    @return  :bool                       Whether the entire program should exit
    '''
    id = feed_node['id']
    next_id = 0
    
    entries = []
    years = {}
    with touch('%s/%s' % (root, id)) as feed_flock:
        flock(feed_flock, True)
        feed_info, feed_data = None, None
        try:
            with open('%s/%s' % (root, id), 'rb') as file:
                feed_info = file.read()
            try:
                with open('%s/%s-content' % (root, id), 'rb') as file:
                    feed_data = file.read()
            except:
                pass
            unflock(feed_flock)
            
            feed_info = feed_info.decode('utf-8', 'strict')
            feed_info = eval(feed_info) if len(feed_info) > 0 else {}
            have = set() if 'have' not in feed_info else feed_info['have']
            unread = set() if 'unread' not in feed_info else feed_info['unread']
            
            if feed_data is not None:
                feed_data = eval(feed_data.decode('utf-8', 'strict'))
                for entry in feed_data:
                    entry['new'] = 1 if entry['guid'] in unread else 0
                    pubdate = entry['pubdate']
                    entry['id'] = entry['guid']
                    entry['realtitle'] = entry['title']
                    title = entry['title'].split('\n')[0]
                    entry['title'] = '(%02i:%02i:%02i) %s' % (pubdate[3], pubdate[4], pubdate[5], title)
                    entry['time'] = (pubdate[3] * 60 + pubdate[4]) * 100 + pubdate[5]
                    if pubdate[0] not in years:
                        year_entry = {}
                        years[pubdate[0]] = year_entry
                        entries.append(year_entry)
                        year_entry['year'] = pubdate[0]
                        year_entry['title'] = _('Year %i') % pubdate[0]
                        year_entry['inner'] = []
                        year_entry['id'] = next_id
                        next_id += 1
                    months = years[pubdate[0]]
                    if pubdate[1] not in months:
                        month_entry = {}
                        months[pubdate[1]] = month_entry
                        months['inner'].append(month_entry)
                        month_entry['month'] = pubdate[1]
                        month_entry['title'] = MONTHS[pubdate[1]] if pubdate[1] in MONTHS else str(pubdate[1])
                        month_entry['inner'] = []
                        month_entry['id'] = next_id
                        next_id += 1
                    days = months[pubdate[1]]
                    if pubdate[2] not in days:
                        day_entry = {}
                        days[pubdate[2]] = day_entry
                        days['inner'].append(day_entry)
                        day_entry['day'] = pubdate[2]
                        title =  MONTHS[pubdate[1]][:3] if pubdate[1] in MONTHS else ''
                        title = '%03i-(%02i)%s-%02i' % (pubdate[0], pubdate[1], title, pubdate[2])
                        day_entry['title'] = title
                        day_entry['inner'] = []
                        day_entry['id'] = next_id
                        next_id += 1
                    entires_of_the_day = days[pubdate[2]]['inner']
                    entires_of_the_day.append(entry)
        except:
            pass
    
    entries.sort(key = lambda x : -(x['year']))
    for year in entries:
        year['inner'].sort(key = lambda x : -(x['month']))
        for month in year['inner']:
            month['inner'].sort(key = lambda x : -(x['day']))
            for day in month['inner']:
                day['inner'].sort(key = lambda x : -(x['time']))
    
    tree = Tree(feed_node['title'], entries)
    while True:
        (action, node) = tree.interact()
        if action == 'quit':
            return True
        elif action == 'back':
            return False
        elif action == 'edit':
            pass # TODO
        elif action == 'open':
            pass # TODO
        elif action == 'add':
            pass # "add", add what?
        elif action == 'delete':
            pass # TODO
        elif action == 'read':
            pass # TODO
        elif action == 'unread':
            pass # TODO

