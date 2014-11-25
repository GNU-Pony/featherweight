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


ACTION_MAP = {'e' : 'edit',
              '+' : 'add',
              'd' : 'delete',
              'r' : 'read',
              'R' : 'unread',
              'u' : 'up',
              'j' : 'down',
              'U' : 'out',
              'J' : 'in',
              '\n' : 'open',
              '\t' : 'back',
              'q' : 'quit'}


def remove_node(trees, node_id):
    '''
    Remove the first found (depth first) occurrence of a node in a set of trees
    
    @param   trees:itr<dict<str, _|itr<↑>|¿I?>>  The trees
    @param   node_id:¿I?                         The identifier for the node
    @return  :bool                               Whether the node was found; intended for method internal use
    '''
    for i in range(len(trees)):
        if ('id' in trees[i]) and (trees[i]['id'] == node_id):
            del trees[i]
            return True
        if 'inner' in trees[i]:
            if remove_node(trees[i]['inner'], node_id):
                if len(trees[i]['inner']) == 0:
                    del trees[i]['inner']
                return True
    return False



def insert_node(trees, node_id, node):
    '''
    Insert a new node into the tree
    
    @param   trees:itr<dict<str, _|itr<↑>|¿I?>>  The trees
    @param   node_id:¿I?                         The identifier for the new node's parent
    @param   node:dict<str, _>                   The new node
    @return  :bool                               Whether the node was found; intended for method internal use
    '''
    if node_id is None:
        trees.append(node)
        return True
    for i in range(len(trees)):
        if ('id' in trees[i]) and (trees[i]['id'] == node_id):
            if 'inner' not in trees[i]:
                trees[i]['inner'] = []
            return insert_node(trees[i]['inner'], None, node)
        if 'inner' in trees[i]:
            if insert_node(trees[i]['inner'], node_id, node):
                return True
    return False



def update_node(trees, node_id, values):
    '''
    Update the values of a node in a tree
    
    @param   trees:itr<dict<str, _|itr<↑>|¿I?>>  The trees
    @param   node_id:¿I?                         The identifier for the node
    @param   values:dict<str, ¿?|...>            The new node values, mapping to `...` for deletion
    @return  :bool                               Whether the node was found; intended for method internal use
    '''
    for i in range(len(trees)):
        if ('id' in trees[i]) and (trees[i]['id'] == node_id):
            for key in values.keys():
                value = values[key]
                if value == ...:
                    if key in trees[i]:
                        del trees[i][key]
                else:
                    trees[i][key] = value
            return True
        if 'inner' in trees[i]:
            if update_node(trees[i]['inner'], node_id, values):
                return True
    return False



def update_node_newness(trees, node_id, mod):
    '''
    Update the 'new' value of a node and its ancestors
    
    @param   trees:itr<dict<str, _|itr<↑>|¿I?>>  The trees
    @param   node_id:¿I?                         The identifier for the node
    @param   mod:int                             How much to add to the 'new' value
    @return  :bool                               Whether the node was found; intended for method internal use
    '''
    for i in range(len(trees)):
        if ('id' in trees[i]) and (trees[i]['id'] == node_id):
            trees[i]['new'] += mod
            return True
        if 'inner' in trees[i]:
            if update_node_newness(trees[i]['inner'], node_id, mod):
                trees[i]['new'] += mod
                return True
    return False



class Tree():
    '''
    Feed tree class
    '''
    
    def __init__(self, root, feeds):
        '''
        Constructor
        
        @param  root:str                        The title of the root
        @param  feeds:itr<dict<str, _|itr<↑>>>  Feeds
        '''
        global height, width
        
        self.root = root
        self.feeds = feeds
        
        self.islinux = ('TERM' not in os.environ) or (os.environ['TERM'] == 'linux')
        self.count = Tree.count_new(feeds)
        
        self.select_stack = [(None, None)]
        self.collapsed_count = 0
        
        def autocollapse(feed):
            if 'inner' in feed:
                if ('new' not in feed) or (feed['new'] == 0):
                    feed['expanded'] = False
                    self.collapsed_count += 1
                [autocollapse(feed) for feed in feed['inner']]
        [autocollapse(feed) for feed in feeds]
        
        height_width = Popen('stty size'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
        (height, width) = height_width.decode('utf-8', 'strict')[:-1].split(' ')
        height, width = int(height), int(width)
        
        self.line = 0
        self.curline = 0
        self.lineoff = 0
        self.draw_force = True
        self.draw_line = 0
        self.last_select = None
        self.redraw_root = False
    
    
    @staticmethod
    def count_new(feeds):
        '''
        Recursively count the number of new entries
        
        @param   feeds:itr<dict<str, _|int|itr<↑>>>  The nodes to perform the count over
        @return  :int                                The number of new entries in the node and all its children
        '''
        rc = 0
        for feed in feeds:
            count = 0
            if 'inner' in feed:
                count = Tree.count_new(feed['inner'])
                feed['new'] = count
            elif 'new' in feed:
                count = feed['new']
            rc += count
        return rc
    
    
    @staticmethod
    def is_expanded(feed):
        '''
        Check whether a feed is expanded
        
        @param   feed:dict<str, _|bool>  The feed
        @return  :bool                   Whether the feed is expanded
        '''
        return ('expanded' not in feed) or feed['expanded']
    
    
    @staticmethod
    def is_leaf(node):
        '''
        Check whether a node is a leaf
        
        @param   node:dict<str, _|bool>?  The node
        @return  :bool                    Whether the node is a leaf
        '''
        return (node is not None) and ('inner' not in node)
    
    
    def print_node(self, feed, last, indent, force):
        '''
        Print a node and its children
        
        @param   feed:dict<str, _|itr<↑>|str|int>  The node to print
        @param   last:bool                         Whether the node is the last child in its parent
        @param   indent:str                        The indent string for the parent
        @param   force:bool                        Whether to print even if marked as printed
        '''
        global height, width
        title = feed['title']
        prefix = indent + ('└' if last else '├')
        collapsed = False
        if ('inner' not in feed) or (Tree.is_expanded(feed)):
            prefix += '── ' if self.islinux else '─╼ '
        else:
            collapsed = True
            prefix += '─┘ ' if self.islinux else '─┚ '
        has_new = ('new' in feed) and (feed['new'] > 0)
        if has_new:
            prefix += '\033[01;31m(%i)\033[00m ' % feed['new']
        prefixlen = len('%s--- %s' % (indent, ('(%i) ' % feed['new']) if has_new else ''))
        if prefixlen + len(title) > width:
            if width - prefixlen - 3 >= 0:
                title = title[: width - prefixlen - 3] + '...'
        if self.select_stack[-1][0] is feed:
            title = '\033[01;34m%s\033[00m' % title
        if self.lineoff <= self.curline < self.lineoff + height:
            if self.curline > self.lineoff:
                print()
            if force or ('draw_line' not in feed) or (feed['draw_line'] != self.draw_line):
                print('\033[2K', end = prefix + title)
                feed['draw_line'] = self.draw_line
            self.draw_line += 1
        self.curline += 1
        if self.line >= 0:
            self.line += 1
            if self.select_stack[-1][0] is feed:
                self.line = ~self.line
        if ('inner' in feed):
            if collapsed:
                feed['draw_expanded'] = False
            else:
                inner = feed['inner']
                _force = force or not feed['draw_expanded']
                feed['draw_expanded'] = True
                for feed in inner:
                    self.print_node(feed, feed is inner[-1], indent + ('    ' if last else '│   '), _force)
    
    
    def print_tree(self):
        '''
        Print the entire tree
        '''
        global height, width
        self.line = 0
        self.curline = 0
        height_width = Popen('stty size'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
        (height, width) = height_width.decode('utf-8', 'strict')[:-1].split(' ')
        height, width = int(height), int(width)
        
        if self.last_select is not self.select_stack[-1][0]:
            if self.last_select is not None:
                self.last_select['draw_line'] = -1
            if self.select_stack[-1][0] is not None:
                self.select_stack[-1][0]['draw_line'] = -1
        
        print('\033[H', end = '')
        if self.draw_force:
            print('\033[2J', end = '')
        title = self.root
        if len(self.select_stack) == 1:
            title = '\033[01;34m%s\033[00m' % title
        root, self.redraw_root = self.redraw_root, False
        if root or self.lineoff <= self.curline < self.lineoff + height:
            if root or self.draw_force or ((self.last_select is not None) == (self.select_stack[-1][0] is None)):
                if self.count > 0:
                    print('\033[01;31m(%i)\033[00m ' % self.count, end = '')
                print(title, end = '')
        self.line += 1
        self.curline += 1
        if len(self.select_stack) == 1:
            self.line = ~self.line
        self.draw_line = 1
        for feed in self.feeds:
            self.print_node(feed, feed is self.feeds[-1], '', self.draw_force)
        if self.draw_line < height:
            print('\n\033[J', end = '')
        sys.stdout.flush()
        
        self.last_select = self.select_stack[-1][0]
        
        self.line = ~self.line
        if not (self.lineoff < self.line <= self.lineoff + height):
            self.draw_force = True
            self.lineoff = self.line - height // 2
            if not (self.lineoff < self.line <= self.lineoff + height):
                self.lineoff -= 1
            if self.lineoff < 0:
                self.lineoff = 0
            self.print_tree()
        
        self.draw_force = False
    
    
    def interact(self):
        '''
        Start interaction with the tree
        
        @return  (command, feed):(str, dict<str, _>)  The choosen command and feed
        '''
        global height, width
        self.print_tree()
        
        buf = '\0' * 10
        queued = ''
        while True:
            if queued == '':
                buf += chr(sys.stdin.buffer.read(1)[0])
            else:
                buf += queued[:1]
                queued = queued[1:]
            buf = buf[-10:]
            if buf[-4 : -1] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                pass
            elif buf[-5 : -2] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                pass
            elif buf[-6 : -3] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                a, x, y = ord(buf[-3]), ord(buf[-2]), ord(buf[-1])
                if a == 96:
                    queued += '\033[A' * 3
                elif a == 97:
                    queued += '\033[B' * 3
                elif a == 32:
                    y -= 33
                    if y < 0:
                        y += 256
                    line = self.lineoff + y
                    last = self.select_stack[-1][0]
                    backup = self.select_stack[:]
                    self.select_stack[:] = self.select_stack[:1]
                    tline = 0
                    if line > 0:
                        while tline != line:
                            if self.select_stack[-1][0] is None:
                                if len(self.feeds) > 0:
                                    self.select_stack.append((self.feeds[0], 0))
                                    tline += 1
                            else:
                                (cur, curi) = self.select_stack[-1]
                                if ('inner' in cur) and Tree.is_expanded(cur):
                                    self.select_stack.append((cur['inner'][0], 0))
                                    tline += 1
                                else:
                                    has_next = False
                                    while len(self.select_stack) > 1:
                                        par = self.select_stack[-2][0]
                                        par = self.feeds if par is None else par['inner']
                                        self.select_stack.pop()
                                        if curi + 1 < len(par):
                                            self.select_stack.append((par[curi + 1], curi + 1))
                                            has_next = True
                                            break
                                        (cur, curi) = self.select_stack[-1]
                                    if not has_next:
                                        break
                                    else:
                                        tline += 1
                        if tline == line:
                            backup = None
                    else:
                        backup = None
                    if backup is None:
                        if self.select_stack[-1][0] is last:
                            queued += ' ' if (last is None) or ('inner' in last) else '\n'
                        else:
                            self.print_tree()
                    else:
                        self.select_stack[:] = backup
            elif buf.endswith('\033[A'):
                if self.select_stack[-1][0] is not None:
                    (cur, curi) = self.select_stack[-1]
                    self.select_stack.pop()
                    if curi > 0:
                        par = self.select_stack[-1][0]
                        par = self.feeds if par is None else par['inner']
                        curi -= 1
                        cur = par[curi]
                        self.select_stack.append((cur, curi))
                        while ('inner' in cur) and Tree.is_expanded(cur):
                            curi = len(cur['inner']) - 1
                            cur = cur['inner'][curi]
                            self.select_stack.append((cur, curi))
                    self.print_tree()
            elif buf.endswith('\033[1;5A'):
                if self.select_stack[-1][0] is not None:
                    (cur, curi) = self.select_stack[-1]
                    self.select_stack.pop()
                    if curi > 0:
                        par = self.select_stack[-1][0]
                        par = self.feeds if par is None else par['inner']
                        self.select_stack.append((par[curi - 1], curi - 1))
                    self.print_tree()
            elif buf.endswith('\033[B'):
                if self.select_stack[-1][0] is None:
                    if len(self.feeds) > 0:
                        self.select_stack.append((self.feeds[0], 0))
                        self.print_tree()
                else:
                    (cur, curi) = self.select_stack[-1]
                    if ('inner' in cur) and Tree.is_expanded(cur):
                        self.select_stack.append((cur['inner'][0], 0))
                        self.print_tree()
                    else:
                        backup = self.select_stack[:]
                        while len(self.select_stack) > 1:
                            par = self.select_stack[-2][0]
                            par = self.feeds if par is None else par['inner']
                            self.select_stack.pop()
                            if curi + 1 < len(par):
                                self.select_stack.append((par[curi + 1], curi + 1))
                                backup = None
                                self.print_tree()
                                break
                            (cur, curi) = self.select_stack[-1]
                        if backup is not None:
                            self.select_stack[:] = backup
            elif buf.endswith('\033[1;5B'):
                backup = None
                while self.select_stack[-1][0] is not None:
                    (cur, curi) = self.select_stack[-1]
                    par = self.select_stack[-2][0]
                    par = self.feeds if par is None else par['inner']
                    if curi + 1 < len(par):
                        self.select_stack.pop()
                        self.select_stack.append((par[curi + 1], curi + 1))
                        self.print_tree()
                        break
                    elif self.select_stack[-2][0] is not None:
                        backup = self.select_stack[:]
                        self.select_stack.pop()
                    else:
                        if backup is not None:
                            self.select_stack[:] = backup
                        break
            elif buf.endswith('\033[C'):
                if self.select_stack[-1][0] is None:
                    if len(self.feeds) > 0:
                        self.select_stack.append((self.feeds[0], 0))
                        self.print_tree()
                else:
                    (cur, curi) = self.select_stack[-1]
                    if 'inner' in cur:
                        if not Tree.is_expanded(cur):
                            cur['expanded'] = True
                            self.collapsed_count -= 1
                        self.select_stack.append((cur['inner'][0], 0))
                        self.print_tree()
            elif buf.endswith('\033[D'):
                if len(self.select_stack) > 1:
                    self.select_stack.pop()
                    self.print_tree()
            elif buf.endswith('\033[1;5D'):
                self.select_stack[:] = self.select_stack[:1]
                self.print_tree()
            elif buf.endswith(' ') or (buf.endswith('\n') and not Tree.is_leaf(self.select_stack[-1][0])):
                cur = self.select_stack[-1][0]
                if cur is None:
                    def expand(feed, value):
                        if 'inner' in feed:
                            cur_value = Tree.is_expanded(feed)
                            if cur_value != value:
                                feed['expanded'] = value
                                self.collapsed_count += -1 if value else 1
                            for inner in feed['inner']:
                                expand(inner, value)
                    value = self.collapsed_count != 0
                    for feed in self.feeds:
                        expand(feed, value)
                    self.draw_force = True
                else:
                    if 'inner' in cur:
                        value = not Tree.is_expanded(cur)
                        self.collapsed_count += -1 if value else 1
                        cur['expanded'] = value
                        cur['draw_line'] = -1
                self.print_tree()
            elif buf.endswith(chr(ord('L') - ord('@'))):
                self.draw_force = True
                self.print_tree()
            elif buf.endswith('n') or buf.endswith('P') or buf.endswith('N') or buf.endswith('p'):
                if self.count == 0:
                    continue
                downward = buf.endswith('n') or buf.endswith('P')
                while True:
                    cur = self.select_stack[-1][0]
                    if cur is None:
                        if downward:
                            self.select_stack.append((self.feeds[0], 0))
                        else:
                            self.select_stack.append((self.feeds[-1], len(self.feeds) - 1))
                            while 'inner' in self.select_stack[-1][0]:
                                inners = self.select_stack[-1][0]['inner']
                                self.select_stack.append((inners[-1], len(inners) - 1))
                    elif downward:
                        curi = self.select_stack[-1][1]
                        if 'inner' in cur:
                            self.select_stack.append((cur['inner'][0], 0))
                        else:
                            restart = True
                            while len(self.select_stack) > 1:
                                par = self.select_stack[-2][0]
                                par = self.feeds if par is None else par['inner']
                                self.select_stack.pop()
                                if curi + 1 < len(par):
                                    self.select_stack.append((par[curi + 1], curi + 1))
                                    restart = False
                                    break
                                (cur, curi) = self.select_stack[-1]
                            if restart:
                                self.select_stack[:] = self.select_stack[:1]
                                continue
                    else:
                        curi = self.select_stack[-1][1]
                        self.select_stack.pop()
                        if curi > 0:
                            par = self.select_stack[-1][0]
                            par = self.feeds if par is None else par['inner']
                            curi -= 1
                            cur = par[curi]
                            self.select_stack.append((cur, curi))
                            while 'inner' in cur:
                                curi = len(cur['inner']) - 1
                                cur = cur['inner'][curi]
                                self.select_stack.append((cur, curi))
                        if self.select_stack[-1][0] is None:
                            continue
                    cur = self.select_stack[-1][0]
                    if ('inner' not in cur) and ('new' in cur) and (cur['new'] > 0):
                        break
                for stack_item in self.select_stack[1:]:
                    stack_item = stack_item[0]
                    if not Tree.is_expanded(stack_item):
                        stack_item['expanded'] = True
                        self.collapsed_count -= 1
                        self.draw_force = True
                self.print_tree()
            elif buf[-1] in ACTION_MAP:
                return (ACTION_MAP[buf[-1]], self.select_stack[-1][0])
            elif (buf[-3] != '\033' or buf[-2] != '[') and (buf[-5] != '\033' or buf[-4] != '[' or buf[-2] != ';') and (ord('0') <= ord(buf[-1]) <= ord('9')):
                return (buf[-1], self.select_stack[-1][0])

