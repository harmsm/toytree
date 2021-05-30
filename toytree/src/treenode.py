#!/usr/bin/env python

"""
A Node graph object forked from the ete3.Tree Class with 
some functions removed/deprecated (e.g., parsing, distance)
and usually re-implemented at the ToyTree level with faster
execution.

Deprecated:
    - get_distance
    - RF
    - write
New Fix:
    - recursive copy error
    - ...
"""

# TODO: replace all random with numpy.rng
import random
import itertools
from hashlib import md5
from collections import deque
from functools import cmp_to_key
from toytree.src.io.TreeWriter import NewickWriter
from toytree.utils.exceptions import TreeError

DEFAULT_EDGE_LENGTH = 1.
DEFAULT_SUPPORT = 0.


class TreeNode:
    """
    TreeNode (Tree) class is used to store a tree structure. A tree
    consists of a collection of TreeNode instances connected in a
    hierarchical way. Trees can be loaded from the New Hampshire Newick
    format (newick).

    Parameters
    ----------
    newick: str
        Path to the file containing the tree or, alternatively,
        the text string containing the same information.

    format: int
        subnewick format

        ======  ==============================================
        FORMAT  DESCRIPTION
        ======  ==============================================
        0        flexible with support values
        1        flexible with internal node names
        2        all branches + leaf names + internal supports
        3        all branches + all names
        4        leaf branches + leaf names
        5        internal and leaf branches + leaf names
        6        internal branches + leaf names
        7        leaf branches + all names
        8        all names
        9        leaf names
        100      topology only
        ======  ==============================================

    Returns
    --------
    a tree node object which represents the base of the tree.
    """

    def __init__(
        self, 
        newick=None, 
        format=0, 
        dist=None, 
        support=None,
        name=None):

        """doc-string"""
        self._children = []
        self._up = None
        self._dist = DEFAULT_EDGE_LENGTH
        self._support = DEFAULT_SUPPORT
        self._height = 0
        self.features = set([])

        # Add basic features
        self.features.update(["dist", "support", "name", "height"])
        if dist is not None:
            self.dist = dist
        if support is not None:
            self.support = support

        # default root name is empty
        self.name = (name if name is not None else "")

        # Initialize tree
        if newick is not None:
            self._dist = 0.0
            # read_newick(newick, root_node=self, format=format)


    ############################################################
    # properties
    ############################################################
    @property
    def dist(self):
        "TreeNode edge length (distance) feature."
        return self._dist
    @dist.setter
    def dist(self, value):
        try:
            self._dist = float(value)
        except ValueError as err:
            raise TreeError('node dist must be a float number') from err


    # TODO: setting height should change the .dist values...
    # this could also be queried faster if we used the .x and .y 
    # info from Coords, and/or stored the .toroot distances from coords.
    @property
    def height(self):
        # i = 0
        # while self.up:
            # i += self.dist
            # self = self.up
        # return i
        # return sum([
            # self.dist, 
            # sum(i.dist for i in self.iter_ancestors() if not i.is_root()),
        # ])
        _root = self.get_tree_root()
        _treeheight = _root.get_distance(_root.get_farthest_leaf()[0])
        return _treeheight - _root.get_distance(self)


    @height.setter
    def height(self, value):
        try:
            self._height = float(value)
        except ValueError:
            raise TreeError('node support must be a float number')

    @property
    def support(self):
        return self._support
    @support.setter
    def support(self, value):
        try:
            self._support = float(value)
        except ValueError:
            raise TreeError('node support must be a float number')

    @property
    def up(self):
        return self._up
    @up.setter
    def up(self, value):
        if type(value) == type(self) or value is None:
            self._up = value
        else:
            raise TreeError("bad node_up type")

    @property
    def children(self):
        return self._children
    @children.setter
    def children(self, value):
        if type(value) == list and \
           len(set([type(n) == type(self) for n in value])) < 2:
            self._children = value
        else:
            raise TreeError("Incorrect children type")


    ####################################################################
    ## private attributes
    ####################################################################
    ## __bool__ is for compatibility between Py2 and 3
    def __nonzero__(self):
        return True

    def __bool__(self):
        return True

    #def __repr__(self):
    #    return "TreeNode '%s' (%s)" % (self.name, hex(self.__hash__()))

    def __and__(self, value):
        """ Allows executing tree&'A' to obtain the node with name A"""
        value = str(value)
        try:
            first_match = next(self.iter_search_nodes(name=value))
            return first_match
        except StopIteration:
            raise TreeError("Node not found")

    def __add__(self, value):
        """ This allows to sum two trees."""
        # Should a make the sum with two copies of the original trees?
        if type(value) == self.__class__:
            new_root = self.__class__()
            new_root.add_child(self)
            new_root.add_child(value)
            return new_root
        else:
            raise TreeError("Invalid node type")

    def __str__(self):
        """ Print tree in newick format. """
        return self.get_ascii(compact=False, show_internal=False)

    def __contains__(self, item):
        """ Check if item belongs to this node. The 'item' argument must
        be a node instance or its associated name."""
        if isinstance(item, self.__class__):
            return item in set(self.get_descendants())
        elif type(item) == str:
            return item in set([n.name for n in self.traverse()])

    def __len__(self):
        """Node len returns number of children."""
        return len(self.get_leaves())

    def __iter__(self):
        """ Iterator over leaf nodes"""
        return self.iter_leaves()


    def _clone(self):
        """
        Returns a new TreeNode object that is equivalent to a deepcopy() 
        of the original. This is much faster than using deepcopy, and makes
        it much faster to copy toytrees.
        """
        # copies the TreeNode object
        ndict = {}

        # traverse root to tips
        for node in self.traverse("levelorder"):

            # create root node and copy attrs
            if node.is_root():
                cnode = TreeNode()
                cnode.__dict__.update(node.__dict__)
                cnode._children = []
                ndict[node.idx] = cnode

            # every other node is someones' child
            else:
                cnode = ndict[node.idx]

            # attach children and copy attrs
            for child in node.children:
                tmp = TreeNode()
                tmp.__dict__.update(child.__dict__)
                tmp.up = cnode
                tmp._children = []
                cnode.add_child(tmp)
                ndict[child.idx] = tmp
        return ndict[self.idx]



    #################################################################
    ## functions
    #################################################################
    def add_feature(self, pr_name, pr_value):
        """ Add or update a node's feature. """
        setattr(self, pr_name, pr_value)
        self.features.add(pr_name)


    def add_features(self, **features):
        """ Add or update several features. """
        for fname, fvalue in features.items():
            setattr(self, fname, fvalue)
            self.features.add(fname)


    def del_feature(self, pr_name):
        """ Permanently deletes a node's feature."""
        if hasattr(self, pr_name):
            delattr(self, pr_name)
            self.features.remove(pr_name)


    #####################################################################
    ## Topology management
    #####################################################################
    def add_child(self, child=None, name=None, dist=None, support=None):
        """
        Adds a new child to this node. If child node is not suplied
        as an argument, a new node instance will be created.

        Parameters
        ----------
        child: 
            the node instance to be added as a child.
        name: 
            the name that will be given to the child.
        dist: 
            the distance from the node to the child.
        support': 
            the support value of child partition.

        Returns:
        --------
            The child node instance
        """
        if child is None:
            child = self.__class__()
        if name is not None:
            child.name = name
        if dist is not None:
            child.dist = dist
        if support is not None:
            child.support = support

        self.children.append(child)
        child.up = self
        return child


    def remove_child(self, child):
        """
        Removes a child from this node (parent and child
        nodes still exit but are no longer connected).
        """
        try:
            self.children.remove(child)
        except ValueError as e:
            raise TreeError("child not found")
        else:
            child.up = None
            return child


    def add_sister(self, sister=None, name=None, dist=None, split=False):
        """
        Adds a sister to this node. If sister node is not supplied
        as an argument, a new TreeNode instance will be created and
        returned.
        """
        if self.up is None:
            raise TreeError("A parent node is required to add a sister")

        # traditional 'add one tip' method
        if sister is None:
            return self.up.add_child(child=sister, name=name, dist=dist)

        # add a tip or subtree to node creating a polytomy
        if not split:
            # auto-align farthest edge at tip
            # if dist is None:
                # dist = self.up.height - sister.height
            return self.up.add_child(child=sister, name=name, dist=dist)

        # create a new node with dist 'split_dist'
        # create new node shared by sisters as up
        olddist = self.dist
        newnode = self.up.add_child(name='newnode')

        # set sisters as newnode children
        newnode.children = [self, sister]
        
        # remove sisters from old parent
        self.up.children.remove(self)

        # connect sisters to new parent
        self.up = newnode
        sister.up = newnode

        # auto-set distances to both align nicely
        if dist is None:
            newnode.dist = olddist / 2.
            self.dist = olddist / 2.
            if isinstance(split, (int, float)):
                sister.dist = split
            else:
                sister.dist = olddist / 2.
        else:
            sister.dist = dist
            self.dist = split
            newnode.dist = olddist - split
        return newnode



    def remove_sister(self, sister=None):
        """
        Removes a sister node. It has the same effect as
        **`TreeNode.up.remove_child(sister)`**

        If a sister node is not supplied, the first sister will be deleted
        and returned.

        :argument sister: A node instance

        :return: The node removed
        """
        sisters = self.get_sisters()
        if len(sisters) > 0:
            if sister is None:
                sister = sisters.pop(0)
            return self.up.remove_child(sister)


    def delete(self, prevent_nondicotomic=True, preserve_branch_length=False):
        r"""
        Deletes node from the tree structure. Notice that this method
        makes 'disappear' the node from the tree structure. This means
        that children from the deleted node are transferred to the
        next available parent.

        Parameters:
        -----------
        prevent_nondicotomic: 
            When True (default), delete
            function will be execute recursively to prevent single-child
            nodes.

        preserve_branch_length: 
            If True, branch lengths of the deleted nodes are transferred 
            (summed up) to its parent's branch, thus keeping original 
            distances among nodes.

        **Example:**
                / C
          root-|
               |        / B
                \--- H |
                        \ A

          > H.delete() will produce this structure:

                / C
               |
          root-|--B
               |
                \ A

        """

        # get parent node
        parent = self.up

        # if there is one
        if parent:
            if preserve_branch_length:
                if len(self.children) == 1:
                    self.children[0].dist += self.dist
                elif len(self.children) > 1:
                    parent.dist += self.dist

            for ch in self.children:
                parent.add_child(ch)

            parent.remove_child(self)

        # Avoids parents with only one child
        if prevent_nondicotomic and parent and len(parent.children) < 2:
            parent.delete(prevent_nondicotomic=False,
                          preserve_branch_length=preserve_branch_length)


    def detach(self):
        """
        Detachs this node (and all its descendants) from its parent
        and returns the referent to itself.

        Detached node conserves all its structure of descendants, and can
        be attached to another node through the 'add_child' function. This
        mechanism can be seen as a cut and paste.
        """
        if self.up:
            self.up.children.remove(self)
            self.up = None
        return self


    def prune(self, nodes, preserve_branch_length=False):
        r"""
        Prunes the topology of a node to conserve only a selected list of leaf
        internal nodes. The minimum number of nodes that conserve the
        topological relationships among the requested nodes will be
        retained. Root node is always conserved.

        Parameters:
        -----------
        nodes:
            a list of node names or node objects that should be retained

        preserve_branch_length: 
            If True, branch lengths of the deleted nodes are transferred 
            (summed up) to its parent's branch, thus keeping original distances
            among nodes.

        **Examples:**
          t1 = Tree('(((((A,B)C)D,E)F,G)H,(I,J)K)root;', format=1)
          t1.prune(['A', 'B'])

          #                /-A
          #          /D /C|
          #       /F|      \-B
          #      |  |
          #    /H|   \-E
          #   |  |                        /-A
          #-root  \-G                 -root
          #   |                           \-B
          #   |   /-I
          #    \K|
          #       \-J

          t1 = Tree('(((((A,B)C)D,E)F,G)H,(I,J)K)root;', format=1)
          t1.prune(['A', 'B', 'C'])

          #                /-A
          #          /D /C|
          #       /F|      \-B
          #      |  |
          #    /H|   \-E
          #   |  |                              /-A
          #-root  \-G                  -root- C|
          #   |                                 \-B
          #   |   /-I
          #    \K|
          #       \-J

          t1 = Tree('(((((A,B)C)D,E)F,G)H,(I,J)K)root;', format=1)
          t1.prune(['A', 'B', 'I'])

          #                /-A
          #          /D /C|
          #       /F|      \-B
          #      |  |
          #    /H|   \-E                    /-I
          #   |  |                      -root
          #-root  \-G                      |   /-A
          #   |                             \C|
          #   |   /-I                          \-B
          #    \K|
          #       \-J

          t1 = Tree('(((((A,B)C)D,E)F,G)H,(I,J)K)root;', format=1)
          t1.prune(['A', 'B', 'F', 'H'])

          #                /-A
          #          /D /C|
          #       /F|      \-B
          #      |  |
          #    /H|   \-E
          #   |  |                              /-A
          #-root  \-G                -root-H /F|
          #   |                                 \-B
          #   |   /-I
          #    \K|
          #       \-J

        """

        def cmp_nodes(x, y):
            # if several nodes are in the same path of two kept nodes,
            # only one should be maintained. This prioritize internal
            # nodes that are already in the to_keep list and then
            # deeper nodes (closer to the leaves).
            if n2depth[x] > n2depth[y]:
                return -1
            elif n2depth[x] < n2depth[y]:
                return 1
            else:
                return 0

        to_keep = set(_translate_nodes(self, *nodes))
        start, node2path = self.get_common_ancestor(to_keep, get_path=True)
        to_keep.add(self)

        # Calculate which kept nodes are visiting the same nodes in
        # their path to the common ancestor.
        n2count = {}
        n2depth = {}
        for seed, path in node2path.items():
            for visited_node in path:
                if visited_node not in n2depth:
                    depth = visited_node.get_distance(start, topology_only=True)
                    n2depth[visited_node] = depth
                if visited_node is not seed:
                    n2count.setdefault(visited_node, set()).add(seed)

        # if several internal nodes are in the path of exactly the same kept
        # nodes, only one (the deepest) should be maintain.
        visitors2nodes = {}
        for node, visitors in n2count.items():
            # keep nodes connection at least two other nodes
            if len(visitors)>1:
                visitor_key = frozenset(visitors)
                visitors2nodes.setdefault(visitor_key, set()).add(node)

        for visitors, nodes in visitors2nodes.items():
            if not (to_keep & nodes):
                sorted_nodes = sorted(nodes, key=cmp_to_key(cmp_nodes))
                to_keep.add(sorted_nodes[0])

        for n in self.get_descendants('postorder'):
            if n not in to_keep:
                if preserve_branch_length:
                    if len(n.children) == 1:
                        n.children[0].dist += n.dist
                    elif len(n.children) > 1 and n.up:
                        n.up.dist += n.dist

                n.delete(prevent_nondicotomic=False)


    def swap_children(self):
        """ Swaps current children order."""
        if len(self.children) > 1:
            self.children.reverse()


    #######################################################
    ## Tree traversing
    #######################################################
    def get_children(self):
        """ Returns an independent list of node's children."""
        return [ch for ch in self.children]


    def get_sisters(self):
        """ Returns an indepent list of sister nodes."""
        if self.up != None:
            return [ch for ch in self.up.children if ch != self]
        else:
            return []


    def iter_leaves(self, is_leaf_fn=None):
        """ Returns an iterator over the leaves under this node."""
        for n in self.traverse(strategy="preorder", is_leaf_fn=is_leaf_fn):
            if not is_leaf_fn:
                if n.is_leaf():
                    yield n
            else:
                if is_leaf_fn(n):
                    yield n


    def get_leaves(self, is_leaf_fn=None):
        """ Returns the list of terminal nodes (leaves) under this node."""
        return [n for n in self.iter_leaves(is_leaf_fn=is_leaf_fn)]


    def iter_leaf_names(self, is_leaf_fn=None):
        """Returns an iterator over the leaf names under this node."""
        for n in self.iter_leaves(is_leaf_fn=is_leaf_fn):
            yield n.name


    def get_leaf_names(self, is_leaf_fn=None):
        """ Returns the list of terminal node names under the current node."""
        return [name for name in self.iter_leaf_names(is_leaf_fn=is_leaf_fn)]


    def iter_descendants(self, strategy="levelorder", is_leaf_fn=None):
        """ Returns an iterator over all descendant nodes."""
        for n in self.traverse(strategy=strategy, is_leaf_fn=is_leaf_fn):
            if n is not self:
                yield n


    def get_descendants(self, strategy="levelorder", is_leaf_fn=None):
        """ Returns a list of all (leaves and internal) descendant nodes."""
        return [n for n in self.iter_descendants(
            strategy=strategy, is_leaf_fn=is_leaf_fn)]


    def traverse(self, strategy="levelorder", is_leaf_fn=None):
        """ Returns an iterator to traverse tree under this node.

        Parameters:
        -----------
        strategy: 
            set the way in which tree will be traversed. Possible 
            values are: "preorder" (first parent and then children)
            'postorder' (first children and the parent) and 
            "levelorder" (nodes are visited in order from root to leaves)

        is_leaf_fn: 
            If supplied, ``is_leaf_fn`` function will be used to 
            interrogate nodes about if they are terminal or internal. 
            ``is_leaf_fn`` function should receive a node instance as first
            argument and return True or False. Use this argument to 
            traverse a tree by dynamically collapsing internal nodes matching
            ``is_leaf_fn``.
        """
        if strategy == "preorder":
            return self._iter_descendants_preorder(is_leaf_fn=is_leaf_fn)
        elif strategy == "levelorder":
            return self._iter_descendants_levelorder(is_leaf_fn=is_leaf_fn)
        elif strategy == "postorder":
            return self._iter_descendants_postorder(is_leaf_fn=is_leaf_fn)


    def iter_prepostorder(self, is_leaf_fn=None):
        """
        Iterate over all nodes in a tree yielding every node in both
        pre and post order. Each iteration returns a postorder flag
        (True if node is being visited in postorder) and a node
        instance.
        """
        to_visit = [self]
        if is_leaf_fn is not None:
            _leaf = is_leaf_fn
        else:
            _leaf = self.__class__.is_leaf

        while to_visit:
            node = to_visit.pop(-1)
            try:
                node = node[1]
            except TypeError:
                # PREORDER ACTIONS
                yield (False, node)
                if not _leaf(node):
                    # ADD CHILDREN
                    to_visit.extend(reversed(node.children + [[1, node]]))
            else:
                #POSTORDER ACTIONS
                yield (True, node)


    def _iter_descendants_postorder(self, is_leaf_fn=None):
        to_visit = [self]
        if is_leaf_fn is not None:
            _leaf = is_leaf_fn
        else:
            _leaf = self.__class__.is_leaf

        while to_visit:
            node = to_visit.pop(-1)
            try:
                node = node[1]
            except TypeError:
                # PREORDER ACTIONS
                if not _leaf(node):
                    # ADD CHILDREN
                    to_visit.extend(reversed(node.children + [[1, node]]))
                else:
                    yield node
            else:
                #POSTORDER ACTIONS
                yield node


    def _iter_descendants_levelorder(self, is_leaf_fn=None):
        """ Iterate over all desdecendant nodes."""
        tovisit = deque([self])
        while len(tovisit) > 0:
            node = tovisit.popleft()
            yield node
            if not is_leaf_fn or not is_leaf_fn(node):
                tovisit.extend(node.children)


    def _iter_descendants_preorder(self, is_leaf_fn=None):
        """ Iterator over all descendant nodes. """
        to_visit = deque()
        node = self
        while node is not None:
            yield node
            if not is_leaf_fn or not is_leaf_fn(node):
                to_visit.extendleft(reversed(node.children))
            try:
                node = to_visit.popleft()
            except:
                node = None


    # toytree: added the 'stopat' option which is used to faster
    # finding of mrca and measuring dist between nodes.
    def iter_ancestors(self, stopat=None):
        """ 
        Iterates over the list of all ancestor nodes from 
        current node to the current tree root.
        """
        node = self
        while node.up is not stopat:
            yield node.up
            node = node.up


    def get_ancestors(self):
        """
        Returns the list of all ancestor nodes from current node to
        the current tree root.
        """
        return [n for n in self.iter_ancestors()]


    def write(
        self, 
        features=None, 
        outfile=None, 
        format=0, 
        is_leaf_fn=None,
        format_root_node=False, 
        dist_formatter=None, 
        support_formatter=None,
        name_formatter=None):
        """
        Returns the newick representation of current node. Several
        arguments control the way in which extra data is shown for
        every node:

        Parameters:
        -----------
        features: 
            a list of feature names to be exported using the Extended Newick 
            Format (i.e. features=["name", "dist"]). Use an empty list to 
            export all available features in each node (features=[])

        outfile:
            writes the output to a given file

        format: 
            defines the newick standard used to encode the tree. 

        format_root_node: 
            If True, it allows features and branch information from root node
            to be exported as a part of the newick text string. For newick 
            compatibility reasons, this is False by default.

        is_leaf_fn: 
            See :func:`TreeNode.traverse` for documentation.
        """
        writer = NewickWriter(
            self, 
            tree_format=format, 
            features=features,
            format_root_node=False, 
            # is_leaf_fn=is_leaf_fn,
            dist_formatter=dist_formatter,
            support_formatter=support_formatter,
            name_formatter=name_formatter,
            )
        newick = writer.write_newick()

        if outfile is not None:
            with open(outfile, "w") as OUT:
                OUT.write(newick)
        else:
            return newick


    def get_tree_root(self):
        """ Returns the absolute root node of current tree structure."""
        root = self
        while root.up is not None:
            root = root.up
        return root


    def get_common_ancestor(self, *target_nodes, **kargs):
        """
        Returns the first common ancestor between this node and a given
        list of 'target_nodes'.

        **Examples:**
          t = tree.Tree("(((A:0.1, B:0.01):0.001, C:0.0001):1.0[&&NHX:name=common], (D:0.00001):0.000001):2.0[&&NHX:name=root];")
          A = t.get_descendants_by_name("A")[0]
          C = t.get_descendants_by_name("C")[0]
          common =  A.get_common_ancestor(C)
          print common.name
        """
        get_path = kargs.get("get_path", False)

        if len(target_nodes) == 1 and type(target_nodes[0]) \
                in set([set, tuple, list, frozenset]):
            target_nodes = target_nodes[0]

        # Convert node names into node instances
        target_nodes = _translate_nodes(self, *target_nodes)

        # If only one node is provided, use self as the second target
        if type(target_nodes) != list:
            target_nodes = [target_nodes, self]

        n2path = {}
        reference = []
        ref_node = None
        for n in target_nodes:
            current = n
            while current:
                n2path.setdefault(n, set()).add(current)
                if not ref_node:
                    reference.append(current)
                current = current.up
            if not ref_node:
                ref_node = n

        common = None
        for n in reference:
            broken = False
            for node, path in n2path.items():
                if node is not ref_node and n not in path:
                    broken = True
                    break

            if not broken:
                common = n
                break
        if not common:
            raise TreeError("Nodes are not connected!")

        if get_path:
            return common, n2path
        else:
            return common


    def iter_search_nodes(self, **conditions):
        """
        Search nodes in an interative way. Matches are being yield as
        they are being found. This avoids to scan the full tree
        topology before returning the first matches. Useful when
        dealing with huge trees.
        """
        for n in self.traverse():
            conditions_passed = 0
            for key, value in conditions.items():
                if hasattr(n, key) and getattr(n, key) == value:
                    conditions_passed +=1
            if conditions_passed == len(conditions):
                yield n


    def search_nodes(self, **conditions):
        """
        Returns the list of nodes matching a given set of conditions.
        **Example:**
        tree.search_nodes(dist=0.0, name="human")
        """
        matching_nodes = []
        for n in self.iter_search_nodes(**conditions):
            matching_nodes.append(n)
        return matching_nodes


    def get_leaves_by_name(self, name):
        """ Returns a list of leaf nodes matching a given name."""
        return self.search_nodes(name=name, children=[])


    def is_leaf(self):
        """ Return True if current node is a leaf."""
        return len(self.children) == 0


    def is_root(self):
        """
        Returns True if current node has no parent
        """
        if self.up is None:
            return True
        else:
            return False

    #########################################################
    # Distance related functions
    #########################################################
    # Error: TreeNode.get_distance(7, 6) != TreeNode.get_distance(6, 7)
    # TODO: deprecate whereever possible, but leave as legacy for ete
    # users. Replace with Toytree funcs.
    def get_distance(self, target, target2=None, topology_only=False):
        """
        Returns the distance between two nodes. If only one target is
        specified, it returns the distance bewtween the target and the
        current node.

        Parameters:
        -----------
        target: 
            a node within the same tree structure.

        target2: 
            a node within the same tree structure. If not specified, 
            current node is used as target2.

        topology_only: 
            If set to True, distance will refer to the number of nodes 
            between target and target2.

        Returns:
        --------
        branch length distance between target and target2. If topology_only 
        flag is True, returns the number of nodes between target and target2.
        """
        if target2 is None:
            target2 = self
            root = self.get_tree_root()
        else:
            # is target node under current node?
            root = self

        target, target2 = _translate_nodes(root, target, target2)
        ancestor = root.get_common_ancestor(target, target2)

        dist = 0.0
        for n in [target2, target]:
            current = n
            while current != ancestor:
                if topology_only:
                    if current != target:
                        dist += 1
                else:
                    dist += current.dist
                current = current.up
        return dist


    def get_farthest_node(self, topology_only=False):
        """
        Returns the node's farthest descendant or ancestor node, and the
        distance to it.

        :argument False topology_only: If set to True, distance
          between nodes will be referred to the number of nodes
          between them. In other words, topological distance will be
          used instead of branch length distances.

        :return: A tuple containing the farthest node referred to the
          current node and the distance to it.

        """
        # Init fasthest node to current farthest leaf
        farthest_node, farthest_dist = self.get_farthest_leaf(
            topology_only=topology_only)

        prev = self
        cdist = 0.0 if topology_only else prev.dist
        current = prev.up
        while current is not None:
            for ch in current.children:
                if ch != prev:
                    if not ch.is_leaf():
                        fnode, fdist = ch.get_farthest_leaf(
                            topology_only=topology_only)
                    else:
                        fnode = ch
                        fdist = 0
                    if topology_only:
                        fdist += 1.0
                    else:
                        fdist += ch.dist
                    if cdist+fdist > farthest_dist:
                        farthest_dist = cdist + fdist
                        farthest_node = fnode
            prev = current
            if topology_only:
                cdist += 1
            else:
                cdist  += prev.dist
            current = prev.up
        return farthest_node, farthest_dist


    def _get_farthest_and_closest_leaves(self, topology_only=False, is_leaf_fn=None):
        # if called from a leaf node, no necessary to compute
        if (is_leaf_fn and is_leaf_fn(self)) or self.is_leaf():
            return self, 0.0, self, 0.0

        min_dist = None
        min_node = None
        max_dist = None
        max_node = None
        d = 0.0
        for post, n in self.iter_prepostorder(is_leaf_fn=is_leaf_fn):
            if n is self:
                continue
            if post:
                d -= n.dist if not topology_only else 1.0
            else:
                if (is_leaf_fn and is_leaf_fn(n)) or n.is_leaf():
                    total_d = d + n.dist if not topology_only else d
                    if min_dist is None or total_d < min_dist:
                        min_dist = total_d
                        min_node = n
                    if max_dist is None or total_d > max_dist:
                        max_dist = total_d
                        max_node = n
                else:
                    d += n.dist if not topology_only else 1.0
        return min_node, min_dist, max_node, max_dist


    def get_farthest_leaf(self, topology_only=False, is_leaf_fn=None):
        """
        Returns node's farthest descendant node (which is always a leaf)
        and the distance to it.

        :argument False topology_only: If set to True, distance
          between nodes will be referred to the number of nodes
          between them. In other words, topological distance will be
          used instead of branch length distances.

        :return: A tuple containing the farthest leaf referred to the
          current node and the distance to it.
        """
        min_node, min_dist, max_node, max_dist = (
            self._get_farthest_and_closest_leaves(
                topology_only=topology_only, 
                is_leaf_fn=is_leaf_fn,
            )
        )
        return max_node, max_dist


    def get_closest_leaf(self, topology_only=False, is_leaf_fn=None):
        """
        Returns node's closest descendant leaf and the distance to it.

        :argument False topology_only: If set to True, distance
          between nodes will be referred to the number of nodes
          between them. In other words, topological distance will be
          used instead of branch length distances.

        :return: A tuple containing the closest leaf referred to the
          current node and the distance to it.

        """
        min_node, min_dist, max_node, max_dist = self._get_farthest_and_closest_leaves(
            topology_only=topology_only, is_leaf_fn=is_leaf_fn)

        return min_node, min_dist


    def get_midpoint_outgroup(self):
        """
        Returns the node that divides the current tree into two 
        distance-balanced partitions.
        """
        # Gets the farthest node to the current root
        root = self.get_tree_root()
        nA, r2A_dist = root.get_farthest_leaf()
        nB, A2B_dist = nA.get_farthest_node()

        outgroup = nA
        middist = A2B_dist / 2.0
        cdist = 0
        current = nA
        while current is not None:
            cdist += current.dist
            if cdist > (middist): # Deja de subir cuando se pasa del maximo
                break
            else:
                current = current.up
        return current


    def populate(
        self, 
        size, 
        names_library=None, 
        reuse_names=False,
        random_branches=False, 
        branch_range=(0, 1),
        support_range=(0, 1)):
        """
        Generates a random topology by populating current node.

        :argument None names_library: If provided, names library
          (list, set, dict, etc.) will be used to name nodes.

        :argument False reuse_names: If True, node names will not be
          necessarily unique, which makes the process a bit more
          efficient.

        :argument False random_branches: If True, branch distances and support
          values will be randomized.

        :argument (0,1) branch_range: If random_branches is True, this
        range of values will be used to generate random distances.

        :argument (0,1) support_range: If random_branches is True,
        this range of values will be used to generate random branch
        support values.

        """
        NewNode = self.__class__

        if len(self.children) > 1:
            connector = NewNode()
            for ch in self.get_children():
                ch.detach()
                connector.add_child(child=ch)
            root = NewNode()
            self.add_child(child=connector)
            self.add_child(child=root)
        else:
            root = self

        next_deq = deque([root])
        for i in range(size - 1):
            if random.randint(0, 1):
                p = next_deq.pop()
            else:
                p = next_deq.popleft()

            c1 = p.add_child()
            c2 = p.add_child()
            next_deq.extend([c1, c2])
            if random_branches:
                c1.dist = random.uniform(*branch_range)
                c2.dist = random.uniform(*branch_range)
                c1.support = random.uniform(*branch_range)
                c2.support = random.uniform(*branch_range)
            else:
                c1.dist = 1.0
                c2.dist = 1.0
                c1.support = 1.0
                c2.support = 1.0

        # next contains leaf nodes
        charset = "abcdefghijklmnopqrstuvwxyz"
        if names_library:
            names_library = deque(names_library)
        else:
            avail_names = itertools.combinations_with_replacement(charset, 10)
        for n in next_deq:
            if names_library:
                if reuse_names:
                    tname = random.sample(names_library, 1)[0]
                else:
                    tname = names_library.pop()
            else:
                tname = ''.join(next(avail_names))
            n.name = tname


    # this is left here for now, but not used by toytree.root()
    def set_outgroup(self, outgroup):
        """
        Sets a descendant node as the outgroup of a tree.  This function
        can be used to root a tree or even an internal node.

        Parameters:
        -----------
        outgroup: 
            a node instance within the same tree structure that will be 
            used as a basal node.
        """
        outgroup = _translate_nodes(self, outgroup)

        if self == outgroup:
            ##return
            ## why raise an error for this?
            raise TreeError("Cannot set myself as outgroup")

        parent_outgroup = outgroup.up

        # Detects (sub)tree root
        n = outgroup
        while n.up is not self:
            n = n.up

        # If outgroup is a child from root, but with more than one
        # sister nodes, creates a new node to group them

        self.children.remove(n)
        if len(self.children) != 1:
            down_branch_connector = self.__class__()
            down_branch_connector.dist = 0.0
            down_branch_connector.support = n.support
            for ch in self.get_children():
                down_branch_connector.children.append(ch)
                ch.up = down_branch_connector
                self.children.remove(ch)
        else:
            down_branch_connector = self.children[0]

        # Connects down branch to myself or to outgroup
        quien_va_ser_padre = parent_outgroup
        if quien_va_ser_padre is not self:
            # Parent-child swapping
            quien_va_ser_hijo = quien_va_ser_padre.up
            quien_fue_padre = None
            buffered_dist = quien_va_ser_padre.dist
            buffered_support = quien_va_ser_padre.support

            while quien_va_ser_hijo is not self:
                quien_va_ser_padre.children.append(quien_va_ser_hijo)
                quien_va_ser_hijo.children.remove(quien_va_ser_padre)

                buffered_dist2 = quien_va_ser_hijo.dist
                buffered_support2 = quien_va_ser_hijo.support
                quien_va_ser_hijo.dist = buffered_dist
                quien_va_ser_hijo.support = buffered_support
                buffered_dist = buffered_dist2
                buffered_support = buffered_support2

                quien_va_ser_padre.up = quien_fue_padre
                quien_fue_padre = quien_va_ser_padre

                quien_va_ser_padre = quien_va_ser_hijo
                quien_va_ser_hijo = quien_va_ser_padre.up

            quien_va_ser_padre.children.append(down_branch_connector)
            down_branch_connector.up = quien_va_ser_padre
            quien_va_ser_padre.up = quien_fue_padre

            down_branch_connector.dist += buffered_dist
            outgroup2 = parent_outgroup
            parent_outgroup.children.remove(outgroup)
            outgroup2.dist = 0

        else:
            outgroup2 = down_branch_connector

        outgroup.up = self
        outgroup2.up = self
        # outgroup is always the first children. Some function my
        # trust on this fact, so do no change this.
        self.children = [outgroup,outgroup2]
        middist = (outgroup2.dist + outgroup.dist)/2
        outgroup.dist = middist
        outgroup2.dist = middist
        outgroup2.support = outgroup.support


    # updated from ete to include preservation of support values.
    def unroot(self):
        """
        Unroots current node. This function is expected to be used on
        the absolute tree root node, but it can be also be applied to
        any other internal node. It will convert a split into a
        multifurcation. 

        toytree: Unlike the ete function, this one inherits node 
        values from the collapsed node into the root to preserve them. 
        """
        # must be bifurcating to start
        if len(self.children)==2:

            # find a child with children 
            if not self.children[0].is_leaf():
                child = self.children[0]
                ochild = self.children[1]
            elif not self.children[1].is_leaf():
                child = self.children[1]
                ochild = self.children[0]
            else:
                raise TreeError("Cannot unroot a tree with only two leaves")

            # update tree for new connection (new)
            for gchild in child.children:
                gchild.up = self
                self.children.append(gchild)
            self.support = child.support
            # self.dist = sum([i.dist for i in self.children])
            ochild.dist += child.dist
            self.children.remove(child)


    def _asciiArt(self, char1='-', show_internal=True, compact=False, attributes=None):
        """
        Returns the ASCII representation of the tree.
        Code based on the PyCogent GPL project.
        """
        if not attributes:
            attributes = ["name"]

        # toytree edit:
        # removed six dependency for map with comprehension
        # node_name = ', '.join(map(str, [getattr(self, v) for v in attributes if hasattr(self, v)]))
        _attrlist = [getattr(self, v) for v in attributes if hasattr(self, v)]
        node_name = ", ".join([str(i) for i in _attrlist])

        LEN = max(3, len(node_name) if not self.children or show_internal else 3)
        PAD = ' ' * LEN
        PA = ' ' * (LEN-1)
        if not self.is_leaf():
            mids = []
            result = []
            for c in self.children:
                if len(self.children) == 1:
                    char2 = '/'
                elif c is self.children[0]:
                    char2 = '/'
                elif c is self.children[-1]:
                    char2 = '\\'
                else:
                    char2 = '-'
                (clines, mid) = c._asciiArt(char2, show_internal, compact, attributes)
                mids.append(mid+len(result))
                result.extend(clines)
                if not compact:
                    result.append('')
            if not compact:
                result.pop()
            (lo, hi, end) = (mids[0], mids[-1], len(result))
            prefixes = [PAD] * (lo+1) + [PA+'|'] * (hi-lo-1) + [PAD] * (end-hi)
            mid = int((lo + hi) / 2)
            prefixes[mid] = char1 + '-'*(LEN-2) + prefixes[mid][-1]
            result = [p+l for (p,l) in zip(prefixes, result)]
            if show_internal:
                stem = result[mid]
                result[mid] = stem[0] + node_name + stem[len(node_name)+1:]
            return (result, mid)
        else:
            return ([char1 + '-' + node_name], 0)


    def get_ascii(self, show_internal=True, compact=False, attributes=None):
        """
        Returns a string containing an ascii drawing of the tree.

        Parameters:
        -----------
        show_internal: 
            include internal edge names.
        compact: 
            use exactly one line per tip.
        attributes: 
            A list of node attributes to shown in the ASCII representation.
        """
        (lines, mid) = self._asciiArt(show_internal=show_internal,
                                      compact=compact, 
                                      attributes=attributes)
        return '\n'+'\n'.join(lines)


    def ladderize(self, direction=0):
        """
        Sort the branches of a given tree (swapping children nodes)
        according to the size of each partition.
        """
        if not self.is_leaf():

            # record nodes and their sizes
            n2s = {}

            # apply dynamic func to children until we get to the tips
            for n in self.get_children():
                s = n.ladderize(direction=direction)
                n2s[n] = s

            # option to also sort tipnames alphanumerically
            # if all([i.is_leaf() for i in self.children]):
            # self.children.sort(key=lambda x: x.name)
            # else:

            # sort nodes by size
            self.children.sort(key=lambda x: n2s[x])

            # flip order for direction arg
            if direction == 1:
                self.children.reverse()

            # get new size
            size = sum(n2s.values())
        else:
            size = 1
        return size


    def sort_descendants(self, attr="name"):
        """
        This function sort the branches of a given tree by
        considerening node names. After the tree is sorted, nodes are
        labeled using ascendent numbers.  This can be used to ensure
        that nodes in a tree with the same node names are always
        labeled in the same way. Note that if duplicated names are
        present, extra criteria should be added to sort nodes.

        Unique id is stored as a node._nid attribute
        """
        node2content = self.get_cached_content(store_attr=attr, container_type=list)
        for n in self.traverse():
            if not n.is_leaf():
                n.children.sort(key=lambda x: str(sorted(node2content[x])))


    def get_cached_content(self, store_attr=None, container_type=set, _store=None):
        """
        Returns a dictionary pointing to the preloaded content of each
        internal node under this tree. Such a dictionary is intended
        to work as a cache for operations that require many traversal
        operations.

        Parameters:
        -----------
        store_attr: 
            Specifies the node attribute that should be cached (i.e. name, 
            distance, etc.). When none, the whole node instance is cached.
        _store: (internal use)
        """
        # create an empty dict or use supplied one
        if _store is None:
            _store = {}

        # add each node info to the dict
        for ch in self.children:
            ch.get_cached_content(
                store_attr=store_attr,
                container_type=container_type,
                _store=_store,
            )

        if self.children:
            val = container_type()
            for ch in self.children:
                if type(val) == list:
                    val.extend(_store[ch])
                if type(val) == set:
                    val.update(_store[ch])
            _store[self] = val
        else:
            if store_attr is None:
                val = self
            else:
                val = getattr(self, store_attr)
            _store[self] = container_type([val])

        return _store


    # def robinson_foulds(
    #     self, 
    #     t2, 
    #     attr_t1="name", 
    #     attr_t2="name",
    #     unrooted_trees=False, 
    #     expand_polytomies=False,
    #     polytomy_size_limit=5, 
    #     skip_large_polytomies=False,
    #     correct_by_polytomy_size=False, 
    #     min_support_t1=0.0,
    #     min_support_t2=0.0):
    #     """
    #     Returns the Robinson-Foulds symmetric distance between current
    #     tree and a different tree instance.

    #     Parameters:
    #     -----------
    #     t2: 
    #         reference tree
    #     attr_t1: 
    #         Compare trees using a custom node attribute as a node name.
    #     attr_t2: 
    #         Compare trees using a custom node attribute as a node name in t2.
    #     attr_t2: 
    #         If True, consider trees as unrooted.
    #     False expand_polytomies: 
    #         If True, all polytomies in the reference and target tree will be 
    #         expanded into all possible binary trees. Robinson-foulds distance 
    #         will be calculated between all tree combinations and the minimum 
    #         value will be returned.
    #         See also, :func:`NodeTree.expand_polytomy`.

    #     Returns:
    #     --------
    #     (rf, rf_max, common_attrs, names, edges_t1, edges_t2, 
    #      discarded_edges_t1, discarded_edges_t2)
    #     """
    #     rf = RobinsonFoulds(
    #         self, t2, 
    #         attr_t1, attr_t2, 
    #         unrooted_trees,
    #         expand_polytomies,
    #         polytomy_size_limit,
    #         skip_large_polytomies,
    #         correct_by_polytomy_size,
    #         min_support_t1,
    #         min_support_t2,
    #         )
    #     return rf.compare_trees()


    # def compare(self, 
    #     ref_tree, 
    #     use_collateral=False, 
    #     min_support_source=0.0, 
    #     min_support_ref=0.0,
    #     has_duplications=False, 
    #     expand_polytomies=False, 
    #     unrooted=False,
    #     max_treeko_splits_to_be_artifact=1000, 
    #     ref_tree_attr='name', 
    #     source_tree_attr='name'):
    #     """
    #     compare this tree with another using robinson foulds symmetric difference
    #     and number of shared edges. Trees of different sizes and with duplicated
    #     items allowed.

    #     returns: a Python dictionary with results
    #     """
    #     source_tree = self

    #     def _safe_div(a, b):
    #         if a != 0:
    #             return a / float(b)
    #         else: return 0.0

    #     def _compare(src_tree, ref_tree):
    #         # calculate partitions and rf distances
    #         rf, maxrf, common, ref_p, src_p, ref_disc, src_disc  = ref_tree.robinson_foulds(src_tree,
    #                                                                                         expand_polytomies=expand_polytomies,
    #                                                                                         unrooted_trees=unrooted,
    #                                                                                         attr_t1=ref_tree_attr,
    #                                                                                         attr_t2=source_tree_attr,
    #                                                                                         min_support_t2=min_support_source,
    #                                                                                         min_support_t1=min_support_ref)

    #         # if trees share leaves, count their distances
    #         if len(common) > 0 and src_p and ref_p:
    #             if unrooted:
    #                 valid_ref_edges = set([p for p in (ref_p - ref_disc) if len(p[0])>1 and len(p[1])>0])
    #                 valid_src_edges = set([p for p in (src_p - src_disc) if len(p[0])>1 and len(p[1])>0])
    #                 common_edges = valid_ref_edges & valid_src_edges
    #             else:
                    
    #                 valid_ref_edges = set([p for p in (ref_p - ref_disc) if len(p)>1])
    #                 valid_src_edges = set([p for p in (src_p - src_disc) if len(p)>1])
    #                 common_edges = valid_ref_edges & valid_src_edges
                    
    #         else:
    #             valid_ref_edges = set()
    #             valid_src_edges = set()
    #             common_edges = set()

    #             # # % of ref edges found in tree
    #             # ref_found.append(float(len(p2 & p1)) / reftree_edges)

    #             # # valid edges in target, discard also leaves
    #             # p2bis = set([p for p in (p2-d2) if len(p[0])>1 and len(p[1])>1])
    #             # if p2bis:
    #             #     incompatible_target_branches = float(len((p2-d2) - p1))
    #             #     target_found.append(1 - (incompatible_target_branches / (len(p2-d2))))

    #         return rf, maxrf, len(common), valid_ref_edges, valid_src_edges, common_edges


    #     total_valid_ref_edges = len([n for n in ref_tree.traverse() if n.children and n.support > min_support_ref])
    #     result = {}
    #     if has_duplications:
    #         orig_target_size = len(source_tree)
    #         ntrees, ndups, sp_trees = source_tree.get_speciation_trees(
    #             autodetect_duplications=True, newick_only=True,
    #             target_attr=source_tree_attr, map_features=[source_tree_attr, "support"])

    #         if ntrees < max_treeko_splits_to_be_artifact:
    #             all_rf = []
    #             ref_found = []
    #             src_found = []
    #             tree_sizes = []
    #             all_max_rf = []
    #             common_names = 0

    #             for subtree_nw in sp_trees:

    #                 #if seedid and not use_collateral and (seedid not in subtree_nw):
    #                 #    continue
    #                 subtree = source_tree.__class__(subtree_nw, sp_naming_function = source_tree._speciesFunction)
    #                 if not subtree.children:
    #                     continue

    #                 # only necessary if rf function is going to filter by support
    #                 # value.  It slows downs the analysis, obviously, as it has to
    #                 # find the support for each node in the treeko tree from the
    #                 # original one.
    #                 if min_support_source > 0:
    #                     subtree_content = subtree.get_cached_content(store_attr='name')
    #                     for n in subtree.traverse():
    #                         if n.children:
    #                             n.support = source_tree.get_common_ancestor(subtree_content[n]).support

    #                 total_rf, max_rf, ncommon, valid_ref_edges, valid_src_edges, common_edges = _compare(subtree, ref_tree)

    #                 all_rf.append(total_rf)
    #                 all_max_rf.append(max_rf)
    #                 tree_sizes.append(ncommon)

    #                 if unrooted:
    #                     ref_found_in_src = len(common_edges)/float(len(valid_ref_edges)) if valid_ref_edges else None
    #                     src_found_in_ref = len(common_edges)/float(len(valid_src_edges)) if valid_src_edges else None
    #                 else:
    #                     # in rooted trees, we want to discount the root edge
    #                     # from the percentage of congruence. Otherwise we will never see a 0%
    #                     # congruence for totally different trees
    #                     ref_found_in_src = (len(common_edges)-1)/float(len(valid_ref_edges)-1) if len(valid_ref_edges)>1 else None
    #                     src_found_in_ref = (len(common_edges)-1)/float(len(valid_src_edges)-1) if len(valid_src_edges)>1 else None
                        
    #                 if ref_found_in_src is not None:
    #                     ref_found.append(ref_found_in_src)
                        
    #                 if src_found_in_ref is not None:
    #                     src_found.append(src_found_in_ref)

    #             if all_rf:
    #                 # Treeko speciation distance
    #                 alld = [_safe_div(all_rf[i], float(all_max_rf[i])) for i in range(len(all_rf))]
    #                 a = sum([alld[i] * tree_sizes[i] for i in range(len(all_rf))])
    #                 b = float(sum(tree_sizes))
    #                 treeko_d = a/b if a else 0.0
    #                 result["treeko_dist"] = treeko_d

    #                 result["rf"] = utils.mean(all_rf)
    #                 result["max_rf"] = max(all_max_rf)
    #                 result["effective_tree_size"] = utils.mean(tree_sizes)
    #                 result["norm_rf"] = utils.mean([_safe_div(all_rf[i], float(all_max_rf[i])) for i in range(len(all_rf))])

    #                 result["ref_edges_in_source"] = utils.mean(ref_found)
    #                 result["source_edges_in_ref"] = utils.mean(src_found)
                    
    #                 result["source_subtrees"] = len(all_rf)
    #                 result["common_edges"] = set()
    #                 result["source_edges"] = set()
    #                 result["ref_edges"] = set()
    #     else:
    #         total_rf, max_rf, ncommon, valid_ref_edges, valid_src_edges, common_edges = _compare(source_tree, ref_tree)

    #         result["rf"] = float(total_rf) if max_rf else "NA"
    #         result["max_rf"] = float(max_rf)
    #         if unrooted:
    #             result["ref_edges_in_source"] = len(common_edges)/float(len(valid_ref_edges)) if valid_ref_edges else "NA"
    #             result["source_edges_in_ref"] = len(common_edges)/float(len(valid_src_edges)) if valid_src_edges else "NA"
    #         else:
    #             # in rooted trees, we want to discount the root edge from the
    #             # percentage of congruence. Otherwise we will never see a 0%
    #             # congruence for totally different trees
    #             result["ref_edges_in_source"] = (len(common_edges)-1)/float(len(valid_ref_edges)-1) if len(valid_ref_edges)>1 else "NA"
    #             result["source_edges_in_ref"] = (len(common_edges)-1)/float(len(valid_src_edges)-1) if len(valid_src_edges)>1 else "NA"

    #         result["effective_tree_size"] = ncommon
    #         result["norm_rf"] = total_rf/float(max_rf) if max_rf else "NA"
    #         result["treeko_dist"] = "NA"
    #         result["source_subtrees"] = 1
    #         result["common_edges"] = common_edges
    #         result["source_edges"] = valid_src_edges
    #         result["ref_edges"] = valid_ref_edges
    #     return result


    # def _diff(self, t2, output='topology', attr_t1='name', attr_t2='name', color=True):
    #     """
    #     Show or return the difference between two tree topologies.
    #     :param [raw|table|topology|diffs|diffs_tab] output: Output type
    #     """
    #     from ..tools import ete_diff
    #     difftable = ete_diff.treediff(self, t2, attr1=attr_t1, attr2=attr_t2)
    #     if output == "topology":
    #         ete_diff.show_difftable_topo(difftable, attr_t1, attr_t2, usecolor=color)
    #     elif output == "diffs":
    #         ete_diff.show_difftable(difftable)
    #     elif output == "diffs_tab":
    #         ete_diff.show_difftable_tab(difftable)
    #     elif output == 'table':
    #         rf, rf_max, _, _, _, _, _ = self.robinson_foulds(t2, attr_t1=attr_t1, attr_t2=attr_t2)[:2]
    #         ete_diff.show_difftable_summary(difftable, rf, rf_max)
    #     else:
    #         return difftable


    def iter_edges(self, cached_content=None):
        """
        Iterate over the list of edges of a tree. Each egde is represented as a
        tuple of two elements, each containing the list of nodes separated by
        the edge.
        """
        if not cached_content:
            cached_content = self.get_cached_content()
        all_leaves = cached_content[self]
        for n, side1 in cached_content.items():
            yield (side1, all_leaves - side1)


    def get_edges(self, cached_content=None):
        """
        Returns the list of edges of a tree. Each egde is represented as a
        tuple of two elements, each containing the list of nodes separated by
        the edge.
        """
        return [edge for edge in self.iter_edges(cached_content)]


    # def standardize(self, delete_orphan=True, preserve_branch_length=True):
    #     """
    #     process current tree structure to produce a standardized topology: nodes
    #     with only one child are removed and multifurcations are automatically resolved.
    #     """
    #     self.resolve_polytomy()
    #     for n in self.get_descendants():
    #         if len(n.children) == 1:
    #             n.delete(prevent_nondicotomic=True,
    #                      preserve_branch_length=preserve_branch_length)


    def get_topology_id(self, attr="name"):
        """
        Returns the unique ID representing the topology of the current tree. 
        Two trees with the same topology will produce the same id. If trees are
        unrooted, make sure that the root node is not binary or use the
        tree.unroot() function before generating the topology id.

        This is useful to detect the number of unique topologies over a bunch 
        of trees, without requiring full distance methods.

        The id is, by default, calculated based on the terminal node's names. 
        Any other node attribute could be used instead.
        """
        edge_keys = []
        for s1, s2 in self.get_edges():
            k1 = sorted([getattr(e, attr) for e in s1])
            k2 = sorted([getattr(e, attr) for e in s2])
            edge_keys.append(sorted([k1, k2]))
        return md5(str(sorted(edge_keys)).encode('utf-8')).hexdigest()


    # ################# useful
    # def convert_to_ultrametric(self, tree_length=None, strategy='balanced'):
    #     """
    #     Converts a tree into ultrametric topology (all leaves must have
    #     the same distance to root).
    #     """
    #     node2max_depth = {}
    #     for node in self.traverse("postorder"):
    #         if not node.is_leaf():
    #             max_depth = max([node2max_depth[c] for c in node.children]) + 1
    #             node2max_depth[node] = max_depth
    #         else:
    #             node2max_depth[node] = 1
    #     node2dist = {self: 0.0}
    #     if not tree_length:
    #         most_distant_leaf, tree_length = self.get_farthest_leaf()
    #     else:
    #         tree_length = float(tree_length)

    #     step = tree_length / node2max_depth[self]
    #     for node in self.iter_descendants("levelorder"):
    #         if strategy == "balanced":
    #             node.dist = (tree_length - node2dist[node.up]) / node2max_depth[node]
    #             node2dist[node] =  node.dist + node2dist[node.up]
    #         elif strategy == "fixed":
    #             if not node.is_leaf():
    #                 node.dist = step
    #             else:
    #                 node.dist = tree_length - ((node2dist[node.up]) * step)
    #             node2dist[node] = node2dist[node.up] + 1
    #         node.dist = node.dist



    ########################################## more not so useful stuff
    def check_monophyly(self, 
        values, 
        target_attr, 
        ignore_missing=False,
        unrooted=False):
        """
        Returns True if a given target attribute is monophyletic under
        this node for the provided set of values.

        If not all values are represented in the current tree
        structure, a ValueError exception will be raised to warn that
        strict monophyly could never be reached (this behaviour can be
        avoided by enabling the `ignore_missing` flag.
        
        Parameters:
        -----------
        values: 
            a set of values for which monophyly is expected.
        
        target_attr: 
            node attribute being used to check monophyly (i.e. species for 
            species trees, names for gene family trees, or any custom feature
            present in the tree).

        ignore_missing: 
            Avoid raising an Exception when missing attributes are found.

        unrooted: 
            If True, tree will be treated as unrooted, thus allowing to find
            monophyly even when current outgroup is spliting a monophyletic group.

        Returns: 
        --------
        the following tuple
        IsMonophyletic (boolean),
        clade type ('monophyletic', 'paraphyletic' or 'polyphyletic'),
        leaves breaking the monophyly (set)
        """
        if type(values) != set:

            values = set(values)

        # This is the only time I traverse the tree, then I use cached
        # leaf content
        n2leaves = self.get_cached_content()

        # Raise an error if requested attribute values are not even present
        if ignore_missing:
            found_values = set([getattr(n, target_attr) for n in n2leaves[self]])
            missing_values = values - found_values
            values = values & found_values

        # Locate leaves matching requested attribute values
        targets = set([leaf for leaf in n2leaves[self]
                   if getattr(leaf, target_attr) in values])
        if not ignore_missing:
            if values - set([getattr(leaf, target_attr) for leaf in targets]):
                raise ValueError('The monophyly of the provided values could never be reached, as not all of them exist in the tree.'
                                 ' Please check your target attribute and values, or set the ignore_missing flag to True')

        if unrooted:
            smallest = None
            for side1, side2 in self.iter_edges(cached_content=n2leaves):
                if targets.issubset(side1) and (not smallest or len(side1) < len(smallest)):
                    smallest = side1
                elif targets.issubset(side2) and (not smallest or len(side2) < len(smallest)):
                        smallest = side2
                if smallest is not None and len(smallest) == len(targets):
                    break
            foreign_leaves = smallest - targets
        else:
            # Check monophyly with get_common_ancestor. Note that this
            # step does not require traversing the tree again because
            # targets are node instances instead of node names, and
            # get_common_ancestor function is smart enough to detect it
            # and avoid unnecessary traversing.
            common = self.get_common_ancestor(targets)
            observed = n2leaves[common]
            foreign_leaves = set([leaf for leaf in observed
                              if getattr(leaf, target_attr) not in values])

        if not foreign_leaves:
            return True, "monophyletic", foreign_leaves
        else:
            # if the requested attribute is not monophyletic in this
            # node, let's differentiate between poly and paraphyly.
            poly_common = self.get_common_ancestor(foreign_leaves)
            # if the common ancestor of all foreign leaves is self
            # contained, we have a paraphyly. Otherwise, polyphyly.
            polyphyletic = [leaf for leaf in poly_common if
                            getattr(leaf, target_attr) in values]
            if polyphyletic:
                return False, "polyphyletic", foreign_leaves
            else:
                return False, "paraphyletic", foreign_leaves


    def get_monophyletic(self, values, target_attr):
        """
        Returns a list of nodes matching the provided monophyly
        criteria. For a node to be considered a match, all
        `target_attr` values within and node, and exclusively them,
        should be grouped.

        :param values: a set of values for which monophyly is
            expected.

        :param target_attr: node attribute being used to check
            monophyly (i.e. species for species trees, names for gene
            family trees).
        """
        if type(values) != set:
            values = set(values)

        n2values = self.get_cached_content(store_attr=target_attr)

        is_monophyletic = lambda node: n2values[node] == values
        for match in self.iter_leaves(is_leaf_fn=is_monophyletic):
            if is_monophyletic(match):
                yield match


    def expand_polytomies(self, 
        map_attr="name", 
        polytomy_size_limit=5,
        skip_large_polytomies=False):
        """
        Given a tree with one or more polytomies, this functions returns the
        list of all trees (in newick format) resulting from the combination of
        all possible solutions of the multifurcated nodes.

        .. warning:

           Please note that the number of of possible binary trees grows
           exponentially with the number and size of polytomies. Using this
           function with large multifurcations is not feasible:

           polytomy size: 3 number of binary trees: 3
           polytomy size: 4 number of binary trees: 15
           polytomy size: 5 number of binary trees: 105
           polytomy size: 6 number of binary trees: 945
           polytomy size: 7 number of binary trees: 10395
           polytomy size: 8 number of binary trees: 135135
           polytomy size: 9 number of binary trees: 2027025

        http://ajmonline.org/2010/darwin.php
        """
        class TipTuple(tuple):
            pass

        # recursive function to add leaves
        def add_leaf(tree, label):
            yield (label, tree)
            if not isinstance(tree, TipTuple) and isinstance(tree, tuple):
                for left in add_leaf(tree[0], label):
                    yield (left, tree[1])
                for right in add_leaf(tree[1], label):
                    yield (tree[0], right)

        # recursive function to take subtrees and return as...
        def enum_unordered(labels):
            if len(labels) == 1:
                yield labels[0]
            else:
                for tree in enum_unordered(labels[1:]):
                    for new_tree in add_leaf(tree, labels[0]):
                        yield new_tree

        # traverse tree from tips to root
        n2subtrees = {}
        for n in self.traverse("postorder"):

            # store leaf name for tips
            if n.is_leaf():
                subtrees = [getattr(n, map_attr)]

            # get node descendants
            else:
                subtrees = []

                # get ways of sampling the children 
                ich = itertools.product(*[n2subtrees[ch] for ch in n.children])

                # if not above poly size limit
                if len(n.children) <= polytomy_size_limit:

                    # store subtrees for all enum_ordered children
                    for childtrees in ich:

                        # get all resolutions of this subclade
                        resolutions = [
                            TipTuple(subtree) for subtree in 
                            enum_unordered(childtrees)
                        ]
                        subtrees.extend(resolutions)

                # check if too big of polytomy
                else:
                    if not skip_large_polytomies:
                        raise TreeError(
                            "Found polytomy larger than current limit: {}"
                            .format(len(n.children)))
                    else:
                        for childtrees in ich:
                            subtrees.append(TipTuple(childtrees))

            # store nodename: [desc]
            n2subtrees[n] = subtrees

        # tuples ARE newick format ^_^ (clever!); convert to str tho
        return ["{};".format(nw).replace("'", "") for nw in n2subtrees[self]]


    def resolve_polytomy(
        self, 
        default_dist=0.0, 
        default_support=0.0,
        recursive=True):
        """
        Resolve all polytomies under current node by creating an
        arbitrary dicotomic structure among the affected nodes. This
        function randomly modifies current tree topology and should
        only be used for compatibility reasons (i.e. programs
        rejecting multifurcated node in the newick representation).

        :param 0.0 default_dist: artificial branch distance of new
            nodes.

        :param 0.0 default_support: artificial branch support of new
            nodes.

        :param True recursive: Resolve any polytomy under this
             node. When False, only current node will be checked and fixed.
        """
        def _resolve(node):
            if len(node.children) > 2:
                children = list(node.children)
                node.children = []
                next_node = root = node
                for i in range(len(children) - 2):
                    next_node = next_node.add_child()
                    next_node.dist = default_dist
                    next_node.support = default_support

                next_node = root
                for ch in children:
                    next_node.add_child(ch)
                    if ch != children[-2]:
                        next_node = next_node.children[0]
        target = [self]
        if recursive:
            target.extend([n for n in self.get_descendants()])
        for n in target:
            _resolve(n)



def _translate_nodes(root, *nodes):
    """
    Convert node names into node instances...
    """

    #name2node = {[n, None] for n in nodes if type(n) is str}
    name2node = dict([[n, None] for n in nodes if type(n) is str])
    for n in root.traverse():
        if n.name in name2node:
            if name2node[n.name] is not None:
                raise TreeError("Ambiguous node name: {}".format(str(n.name)))
            else:
                name2node[n.name] = n

    if None in list(name2node.values()):
        notfound = [key for key, value in name2node.items() if value is None]
        raise ValueError("Node names not found: "+str(notfound))

    valid_nodes = []
    for n in nodes:
        if type(n) is not str:
            if type(n) is not root.__class__:
                raise TreeError("Invalid target node: "+str(n))
            else:
                valid_nodes.append(n)

    valid_nodes.extend(list(name2node.values()))
    if len(valid_nodes) == 1:
        return valid_nodes[0]
    else:
        return valid_nodes