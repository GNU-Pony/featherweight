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
import xml.parsers.expat
import sys


feed = sys.argv[1]
with open(feed, 'r') as file:
    feed = file.read()


parser = xml.parsers.expat.ParserCreate()


is_rss = False
feeds = []
rss_root = None
item = None
text = None


def start_element(name, attributes):
    global is_rss, feeds, rss_root, item, text
    name = name.lower()
    if rss_root is None:
        if name == 'rss':
            is_rss = True
        elif is_rss:
            if name == 'channel':
                rss_root = {'items' : []}
                return
    else:
        if item is None:
            if name == 'item':
                item = {}
                return
    text = ''


def end_element(name):
    global is_rss, feeds, rss_root, item, text
    if rss_root is not None:
        if item is not None:
            if name == 'item':
                rss_root['items'].append(item)
                item = None
            elif name == 'title':
                item['title'] = text
            elif name == 'description':
                item['description'] = text
            elif name == 'link':
                item['link'] = text
            elif name == 'guid':
                item['guid'] = text
            elif name == 'pubdate':
                item['pubdate'] = text
        else:
            if name == 'title':
                rss_root['title'] = text
            elif name == 'description':
                rss_root['description'] = text
            elif name == 'link':
                rss_root['link'] = text
            elif name == 'channel':
                feeds.append(rss_root)
                rss_root = None
            elif name == 'rss':
                is_rss = False
    text = None


def char_data(data):
    global text
    if text is not None:
        text += data



parser.StartElementHandler = start_element
parser.EndElementHandler = end_element
parser.CharacterDataHandler = char_data


parser.Parse(feed, True)

print(feeds)

