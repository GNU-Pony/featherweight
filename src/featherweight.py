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
is_atom = False
feeds = []
root = None
item = None
text = None


def rss_date(value):
    return value

def atom_date(value):
    return value


def start_element(name, attributes):
    global is_rss, feeds, root, item, text, is_atom, attrs
    attrs = attributes
    name = name.lower()
    if is_rss:
        if root is None:
            if name == 'channel':
                root = {'items' : []}
        else:
            if item is None:
                if name == 'item':
                    item = {}
    elif is_atom:
        if item is None:
            if name == 'entry':
                item = {}
    elif name == 'rss':
        is_rss = True
    elif name == 'feed':
        is_atom = True
        root = {'items' : []}
    text = ''


def end_element(name):
    global is_rss, feeds, root, item, text, is_atom, attrs
    if (root is not None) and is_rss:
        if item is not None:
            if name == 'item':
                root['items'].append(item)
                item = None
            elif name in ('title', 'description', 'link', 'guid'):
                item[name] = text
            elif name == 'pubdate':
                item['pubdate'] = rss_date(text)
        else:
            if name in ('title', 'description', 'link'):
                root[name] = text
            elif name == 'channel':
                feeds.append(root)
                root = None
            elif name == 'rss':
                is_rss = False
    elif (root is not None) and is_atom:
        if item is not None:
            if name == 'entry':
                root['items'].append(item)
                item = None
            elif name == 'title':
                item['title'] = text
            elif name == 'id':
                item['guid'] = text
            elif name == 'summary':
                if 'description' not in item:
                    item['description'] = text
            elif name == 'content':
                item['description'] = text
            elif name == 'link':
                if 'rel' not in attrs:
                    item['link'] = text
            elif name == 'updated':
                item['pubdate'] = atom_date(text)
        else:
            if name == 'title':
                root['title'] = text
            elif name == 'subtitle':
                root['description'] = text
            elif name == 'link':
                if 'rel' not in attrs:
                    root['link'] = text
            elif name == 'feed':
                feeds.append(root)
                root = None
                is_atom = False
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

