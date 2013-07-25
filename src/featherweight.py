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


rss = sys.argv[1]
with open(rss, 'r') as file:
    rss = file.read()


parser = xml.parsers.expat.ParserCreate()

def start_element(name, attributes):
    print('Start element:', name, attributes)
def end_element(name):
    print('End element:', name)
def char_data(data):
    print('Character data:', repr(data))


parser.StartElementHandler = start_element
parser.EndElementHandler = end_element
parser.CharacterDataHandler = char_data


parser.Parse(rss, True)

