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
              'q' : 'quit',
              '0' : '0', '1' : '1', '2' : '2', '3' : '3', '4' : '4',
              '5' : '5', '6' : '6', '7' : '7', '8' : '8', '9' : '9'}
'''
:dict<str, str>  Keypress to action string map.
'''


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
    
    @variable  root:str                            The title of the root
    @variable  feeds:itr<dict<str, _|itr<↑>>>      Feeds
    @variable  islinux:bool                        Running in Linux VT? This is useful for selecting the
                                                   best characters, as Linux VT has a limited character set.
    @variable  count:int                           The number of new items
    @variable  select_stack:list<(:Tree?, :int?)>  Stack of selected nodes, object and index
    @variable  collapsed_count:int                 The number of collapsed branches
    @variable  line:int                            Used to keep track of whether the vision field
                                                   must be adjusted to make the selected node visible
    @variable  curline:int                         The current line, in the tree, being drawn
    @variable  lineoff:int                         The index of the first visible line
    @variable  draw_force:bool                     Do I need to redraw the screen?
    @variable  draw_line:int                       The current line on the screen
    @variable  last_select:Tree?                   The previously selected node.
    @variable  redraw_root:bool                    Do I need to redraw the root?
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
        
        # Collapes all branches.
        def autocollapse(feed):
            if 'inner' in feed:
                if ('new' not in feed) or (feed['new'] == 0):
                    feed['expanded'] = False
                    self.collapsed_count += 1
                [autocollapse(feed) for feed in feed['inner']]
        [autocollapse(feed) for feed in feeds]
        
        # Get size of terminal.
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
        
        # What is the title on the node?
        title = feed['title']
        
        # Is the node a collapsed branch?
        collapsed = ('inner' in feed) and not Tree.is_expanded(feed)
        
        # What should be printed at the beginning of the line to make it look like a tree?
        prefix = indent + ('└' if last else '├')
        if collapsed:
            prefix += '─┘ ' if self.islinux else '─┚ '
        else:
            prefix += '── ' if self.islinux else '─╼ '
        
        # Anything new in the node?
        has_new = ('new' in feed) and (feed['new'] > 0)
        if has_new:
            prefix += '\033[01;31m(%i)\033[00m ' % feed['new']
        
        # Truncate title if it is too long.
        prefixlen = len('%s--- %s' % (indent, ('(%i) ' % feed['new']) if has_new else ''))
        if prefixlen + len(title) > width:
            if width - prefixlen - 3 >= 0:
                title = title[:width - prefixlen - 3] + '...'
        
        # Get the colour, and selection highlight, for the node.
        if 'colour' in feed:
            if self.select_stack[-1][0] is feed:
                title = '\033[01;3%im%s\033[00m' % (feed['colour'], title)
            else:
                title = '\033[3%im%s\033[00m' % (feed['colour'], title)
        elif self.select_stack[-1][0] is feed:
            title = '\033[01;34m%s\033[00m' % title
        
        # Draw the node.
        if self.lineoff <= self.curline < self.lineoff + height:
            if self.curline > self.lineoff:
                print()
            if force or ('draw_line' not in feed) or (feed['draw_line'] != self.draw_line):
                print('\033[2K', end = prefix + title)
                feed['draw_line'] = self.draw_line
            self.draw_line += 1
        else:
            feed['draw_line'] = -1
        self.curline += 1
        
        # Was the the select node not printed yet?
        if self.line >= 0:
            # Remember that that we just draw the a lnie.
            self.line += 1
            # Select node not printed yet, now?
            if self.select_stack[-1][0] is feed:
                self.line = ~self.line
        
        # Draw children.
        if 'inner' in feed:
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
        
        # Reset line pointers.
        self.line = 0
        self.curline = 0
        
        # Get the size of the terminal.
        height_width = Popen('stty size'.split(' '), stdout = PIPE, stderr = PIPE).communicate()[0]
        (height, width) = height_width.decode('utf-8', 'strict')[:-1].split(' ')
        height, width = int(height), int(width)
        
        # Do we need to redraw the currentöy and the previously selected line.
        if self.last_select is not self.select_stack[-1][0]:
            if self.last_select is not None:
                self.last_select['draw_line'] = -1
            if self.select_stack[-1][0] is not None:
                self.select_stack[-1][0]['draw_line'] = -1
        
        # Go to top of screen, clear if redrawing.
        print('\033[H', end = '')
        if self.draw_force:
            print('\033[2J', end = '')
        # Ge the title of the root, and selection highlight colour.
        title = self.root
        if len(self.select_stack) == 1:
            title = '\033[01;34m%s\033[00m' % title
        # Draw the root.
        root, self.redraw_root = self.redraw_root, False
        if root or self.lineoff <= self.curline < self.lineoff + height:
            if root or self.draw_force or ((self.last_select is not None) == (self.select_stack[-1][0] is None)):
                print('\033[K', end = '')
                if self.count > 0:
                    print('\033[01;31m(%i)\033[00m ' % self.count, end = '')
                print(title, end = '')
        self.line += 1
        self.curline += 1
        # At root? It as been printed.
        if len(self.select_stack) == 1:
            self.line = ~self.line
        self.draw_line = 1
        # Draw children.
        for feed in self.feeds:
            self.print_node(feed, feed is self.feeds[-1], '', self.draw_force)
        # Clear the rest of the screen, there is nothing there.
        if self.draw_line < height:
            print('\n\033[J', end = '')
        sys.stdout.flush()
        
        # Remember which node is selected.
        self.last_select = self.select_stack[-1][0]
        
        # Was the selected node visible?
        self.line = ~self.line
        if not (self.lineoff < self.line <= self.lineoff + height):
            # No. Then:
            # Adjust vision field so the select node is centered..
            self.lineoff = self.line - height // 2
            # If not possible to center, go to boundary.
            if not (self.lineoff < self.line <= self.lineoff + height):
                self.lineoff -= 1
            if self.lineoff < 0:
                self.lineoff = 0
            # Drawn
            self.draw_force = True
            self.print_tree()
        
        # Forced redraw has been applied (if it was requeted.)
        self.draw_force = False
    
    
    def interact(self):
        '''
        Start interaction with the tree
        
        @return  (command, feed):(str, dict<str, _>)  The choosen command and feed
        '''
        global height, width

        # Print the tree.
        self.print_tree()
        
        # Ring buffer for input.
        buf = '\0' * 10
        # Queue of synthetic input.
        queued = ''
        
        # Interact.
        while True:
            # Get input.
            if queued == '':
                buf += chr(sys.stdin.buffer.read(1)[0])
            else:
                buf += queued[:1]
                queued = queued[1:]
            buf = buf[-10:]
            
            # Mouse input is not complete yet.
            if buf[-4 : -1] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                pass
            # Mouse input is not complete yet.
            elif buf[-5 : -2] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                pass
            # Mouse input is now complete.
            elif buf[-6 : -3] == '%s%s%s' % (chr(27), chr(91), chr(77)):
                # Get action, X position, and Y-position.
                a, x, y = ord(buf[-3]), ord(buf[-2]), ord(buf[-1])
                # Scrolled up.
                if a == 96:
                    queued += '\033[A' * 3
                # Scrolled down.
                elif a == 97:
                    queued += '\033[B' * 3
                # Clicked.
                elif a == 32:
                    # Adjust Y-position, it is given with an offset.
                    y -= 33
                    if y < 0:
                        y += 256
                    # Get clicked line in the tree. (Apply vision offset.)
                    line = self.lineoff + y
                    # Get current node.
                    last = self.select_stack[-1][0]
                    # Back up selection stack, and clear it.
                    backup = self.select_stack[:]
                    self.select_stack[:] = self.select_stack[:1]
                    # We begin at the root, its line is 0.
                    tline = 0
                    # Did not click root?
                    if line > 0:
                        # Figure out which node was selected.
                        while tline != line:
                            # At root?
                            if self.select_stack[-1][0] is None:
                                # Visit the first node.
                                if len(self.feeds) > 0:
                                    self.select_stack.append((self.feeds[0], 0))
                                    tline += 1
                            # Not at root?
                            else:
                                (cur, curi) = self.select_stack[-1]
                                # At expanded branch?
                                if ('inner' in cur) and Tree.is_expanded(cur):
                                    # Visit first child.
                                    self.select_stack.append((cur['inner'][0], 0))
                                    tline += 1
                                # At leaf or collapsed branch?
                                else:
                                    has_next = False
                                    # While there is more.
                                    while len(self.select_stack) > 1:
                                        # Get parent.
                                        par = self.select_stack[-2][0]
                                        par = self.feeds if par is None else par['inner']
                                        # We are no longer visiting the node.
                                        self.select_stack.pop()
                                        # Is there another node in the branch?
                                        if curi + 1 < len(par):
                                            # Visit it.
                                            self.select_stack.append((par[curi + 1], curi + 1))
                                            has_next = True
                                            break
                                        # Otherwise, visit to parent.
                                        (cur, curi) = self.select_stack[-1]
                                    # Stop the search if all nodes have been visited.
                                    if not has_next:
                                        break
                                    # Otherwise, keep track on which line in the tree we are on.
                                    else:
                                        tline += 1
                        # Found it?
                        if tline == line:
                            backup = None
                    # Select root if the root was clicked.
                    else:
                        backup = None
                    # Was a node clicked?
                    if backup is None:
                        # Did the user click on the selected node. (Possibily a double click.)
                        if self.select_stack[-1][0] is last:
                            # Expand it.
                            queued += ' ' if (last is None) or ('inner' in last) else '\n'
                        # Otherwise...
                        else:
                            # ... redraw the the retree.
                            self.print_tree()
                    # Did no click on a node? Revert.
                    else:
                        self.select_stack[:] = backup
            
            # Up.
            elif buf.endswith('\033[A'):
                # Not at root?
                if self.select_stack[-1][0] is not None:
                    # No longer at the current node.
                    (cur, curi) = self.select_stack[-1]
                    self.select_stack.pop()
                    # Not at the first node in the branch? (Goes to parent otherwise.)
                    if curi > 0:
                        # Get parent.
                        par = self.select_stack[-1][0]
                        par = self.feeds if par is None else par['inner']
                        # Go to previous node.
                        curi -= 1
                        cur = par[curi]
                        self.select_stack.append((cur, curi))
                        # If the previous node is a branch, find its visible last node.
                        while ('inner' in cur) and Tree.is_expanded(cur):
                            curi = len(cur['inner']) - 1
                            cur = cur['inner'][curi]
                            self.select_stack.append((cur, curi))
                    self.print_tree()
            
            # C-up.
            elif buf.endswith('\033[1;5A'):
                # Not at root?
                if self.select_stack[-1][0] is not None:
                    # No longer at the current node.
                    (cur, curi) = self.select_stack[-1]
                    self.select_stack.pop()
                    # If we were not at the first node in the branch... (Goes to parent otherwise.)
                    if curi > 0:
                        # ... go to the previous node.
                        par = self.select_stack[-1][0]
                        par = self.feeds if par is None else par['inner']
                        self.select_stack.append((par[curi - 1], curi - 1))
                    self.print_tree()
            
            # Down.
            elif buf.endswith('\033[B'):
                # At root?
                if self.select_stack[-1][0] is None:
                    # Go to first node.
                    if len(self.feeds) > 0:
                        self.select_stack.append((self.feeds[0], 0))
                        self.print_tree()
                # Not at root?
                else:
                    (cur, curi) = self.select_stack[-1]
                    # At expanded branch?
                    if ('inner' in cur) and Tree.is_expanded(cur):
                        # Go to first child
                        self.select_stack.append((cur['inner'][0], 0))
                        self.print_tree()
                    # At leaf or or collapsed branch?
                    else:
                        # Back up the current selection stack.
                        backup = self.select_stack[:]
                        # While not a root.
                        while len(self.select_stack) > 1:
                            # Get parent.
                            par = self.select_stack[-2][0]
                            par = self.feeds if par is None else par['inner']
                            # We are no longer at the current node.
                            self.select_stack.pop()
                            # If there is a next node in the branch...
                            if curi + 1 < len(par):
                                # ... go to it.
                                self.select_stack.append((par[curi + 1], curi + 1))
                                backup = None
                                self.print_tree()
                                break
                            # ... otherwise retry from the parent.
                            (cur, curi) = self.select_stack[-1]
                        # Restore the current selection stack if we did not find any node to which to go.
                        if backup is not None:
                            self.select_stack[:] = backup
            
            # C-down.
            elif buf.endswith('\033[1;5B'):
                backup = None
                # Find next node in the branch or and ancestor.
                while self.select_stack[-1][0] is not None:
                    # Get current node, and parent.
                    (cur, curi) = self.select_stack[-1]
                    par = self.select_stack[-2][0]
                    par = self.feeds if par is None else par['inner']
                    # Not at the current last node in the branch?
                    if curi + 1 < len(par):
                        # Go to the next node.
                        self.select_stack.pop()
                        self.select_stack.append((par[curi + 1], curi + 1))
                        self.print_tree()
                        break
                    # At last node in branch.
                    elif self.select_stack[-2][0] is not None:
                        # Try parent.
                        backup = self.select_stack[:]
                        self.select_stack.pop()
                    # Did not find a node?
                    else:
                        # Revert.
                        if backup is not None:
                            self.select_stack[:] = backup
                        break
            
            # Right.
            elif buf.endswith('\033[C'):
                # At root?
                if self.select_stack[-1][0] is None:
                    # Go to first node.
                    if len(self.feeds) > 0:
                        self.select_stack.append((self.feeds[0], 0))
                        self.print_tree()
                # Not at root?
                else:
                    # Go to first child.
                    (cur, curi) = self.select_stack[-1]
                    if 'inner' in cur:
                        if not Tree.is_expanded(cur):
                            # Expand branch whence we came if collapsed.
                            cur['expanded'] = True
                            self.collapsed_count -= 1
                        self.select_stack.append((cur['inner'][0], 0))
                        self.print_tree()
            
            # TODO C-right: go to first leaf if in branch
            
            # Left.
            elif buf.endswith('\033[D'):
                # Go to parent.
                if len(self.select_stack) > 1:
                    self.select_stack.pop()
                    self.print_tree()
            
            # C-left.
            elif buf.endswith('\033[1;5D'):
		# Go to root.
                self.select_stack[:] = self.select_stack[:1]
                self.print_tree()
            
            # Space or, not at a branch, enter.
            elif buf.endswith(' ') or (buf.endswith('\n') and not Tree.is_leaf(self.select_stack[-1][0])):
                cur = self.select_stack[-1][0]
                # At root?
                if cur is None:
                    # Expand or collapse all nodes.
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
                # Not at root?
                else:
                    # But at a branch?
                    if 'inner' in cur:
                        # Expand or collapse branch.
                        value = not Tree.is_expanded(cur)
                        self.collapsed_count += -1 if value else 1
                        cur['expanded'] = value
                        cur['draw_line'] = -1
                self.print_tree()
            
            # C-l.
            elif buf.endswith(chr(ord('L') - ord('@'))):
                # Redraw everything.
                self.draw_force = True
                self.print_tree()
            
            # n, P, N, or p. (Jump to unread leaf.)
            elif buf.endswith('n') or buf.endswith('P') or buf.endswith('N') or buf.endswith('p'):
                # No unread leafs?
                if self.count == 0:
                    continue
                # Which direction?
                downward = buf.endswith('n') or buf.endswith('P')
                # Locate next/previous unread leaf.
                while True:
                    cur = self.select_stack[-1][0]
                    # At root.
                    if cur is None:
                        # Test first node.
                        if downward:
                            self.select_stack.append((self.feeds[0], 0))
                        # Test last node.
                        else:
                            self.select_stack.append((self.feeds[-1], len(self.feeds) - 1))
                            while 'inner' in self.select_stack[-1][0]:
                                inners = self.select_stack[-1][0]['inner']
                                self.select_stack.append((inners[-1], len(inners) - 1))
                    # Find next.
                    elif downward:
                        curi = self.select_stack[-1][1]
                        # On branch? Visit its children.
                        if 'inner' in cur:
                            self.select_stack.append((cur['inner'][0], 0))
                        # Otherwise, test next, possibility and ancestors next.
                        else:
                            restart = True
                            # While we are not at root.
                            while len(self.select_stack) > 1:
                                # Get parent.
                                par = self.select_stack[-2][0]
                                par = self.feeds if par is None else par['inner']
                                # We are no longer at current node.
                                self.select_stack.pop()
                                # Not at the last node in the branch?
                                if curi + 1 < len(par):
                                    # Select the next one.
                                    self.select_stack.append((par[curi + 1], curi + 1))
                                    restart = False
                                    break
                                (cur, curi) = self.select_stack[-1]
                            # Go to root if we have test everything below the
                            # current node, and continue search from there.
                            if restart:
                                self.select_stack[:] = self.select_stack[:1]
                                continue
                    # Find previous.
                    else:
                        curi = self.select_stack[-1][1]
                        # We are not longer at the current node.
                        self.select_stack.pop()
                        # Not at the first node in the branch?
                        if curi > 0:
                            # Get parent.
                            par = self.select_stack[-1][0]
                            par = self.feeds if par is None else par['inner']
                            # Got to previous node.
                            curi -= 1
                            cur = par[curi]
                            self.select_stack.append((cur, curi))
                            # Is it a branch?
                            while 'inner' in cur:
                                # Select the last node in that branch.
                                curi = len(cur['inner']) - 1
                                cur = cur['inner'][curi]
                                self.select_stack.append((cur, curi))
                                # Repeat, if the new node is also a branch.
                        # Reached the root? Start over, beginning search at the last node in the tree.
                        if self.select_stack[-1][0] is None:
                            continue
                    # Is the leaf unread?
                    cur = self.select_stack[-1][0]
                    if ('inner' not in cur) and ('new' in cur) and (cur['new'] > 0):
                        break
                # Expand collapsed ancestors of the unread leaf.
                for stack_item in self.select_stack[1:]:
                    stack_item = stack_item[0]
                    if not Tree.is_expanded(stack_item):
                        stack_item['expanded'] = True
                        self.collapsed_count -= 1
                        self.draw_force = True
                # Draw.
                self.print_tree()
            
            # Normal keypress.
            elif (buf[-2] not in '[;') and (buf[-1] in ACTION_MAP):
                return (ACTION_MAP[buf[-1]], self.select_stack[-1][0])
            
            # Digit keypress.
            elif (buf[-3] != '\033') or (buf[-2] != '['):
                if (buf[-5] != '\033') or (buf[-4] != '[') or (buf[-2] != ';'):
                    if ord('0') <= ord(buf[-1]) <= ord('9'):
                        return (buf[-1], self.select_stack[-1][0])

