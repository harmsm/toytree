#!/usr/bin/env python

"""Node distance functions.

These functions take a tree as input and use Node int idx labels
to select Nodes.
"""

from typing import TypeVar, Tuple, Union, Dict, Iterator
import itertools
import numpy as np
import pandas as pd
from toytree.utils import ToytreeError


# type aliases
ToyTree = TypeVar("ToyTree")
Node = TypeVar("Node")
Query = TypeVar("Query", str, int, Node, None)

# put functions here to have then exposed to Toytree API
__all__ = [
    "get_node_path",
    "get_node_distance",
    "get_internal_node_distance_matrix",
    "get_node_distance_matrix",
    "get_tip_distance_matrix",
    "get_farthest_node",
    "get_farthest_node_distance",
    "get_node_path",
]


def get_node_path(tree: ToyTree, node0: Query, node1: Query) -> Tuple[Node]:
    """Return a list of Nodes on the path between two Nodes.

    Parameters
    ----------
    tree: ToyTree
        A tree containing the queried Nodes.
    node0: int, str, or Node
        A Node in the tree at the start of the path. Nodes can be
        queried by int idx label, str name, or as Node objects.
    node1: int, str, or Node
        A Node in the tree at the end of the path.

    Example
    -------
    >>> tree = toytree.rtree.imbtree(10)
    >>> tree.distance.get_node_path(0, 2)
    >>> # (Node(idx=10), Node(11))
    """
    return tuple(iter_node_path(tree, node0, node1))


def iter_node_path(tree: ToyTree, node0: Query, node1: Query) -> Iterator[Node]:
    """Generator of the path between two Nodes."""
    node0 = tree.get_nodes(node0)[0]
    yield node0
    node1 = tree.get_nodes(node1)[0]
    mrca = tree.get_mrca_node(node0.idx, node1.idx)
    for node in node0._iter_ancestors(mrca):
        yield node
    yield mrca
    for node in list(node1._iter_ancestors(mrca))[::-1]:
        yield node
    yield node1


# >3X faster than older TreeNode.get_distance(), and scales better.
# If the tree is ultrametric we could calculate 2X faster by just
# doubling the distance to mrca...
def get_node_distance(
    tree: ToyTree,
    node0: Query,
    node1: Query,
    topology_only: bool = False,
) -> float:
    """Return patristic distance between two Nodes on a ToyTree.

    Parameters
    ----------
    tree: toytree.ToyTree
        A ToyTree instance.
    node0: int, str, or Node
        A Node in the tree.
    node1: int, str, or Node
        Another Node in the tree.
    topology_only: bool
        If True then distance is measured as number of edges between
        the two Nodes.

    Returns
    -------
    distance: float
        The patristic distance between two nodes (the minimum
        distance along edges connecting them that passes through
        their common ancestor).

    Example
    -------
    >>> tree = toytree.rtree.unittree(10, seed=123)
    >>> toytree.distance.get_node_distance(tree, 0, 1)
    """
    # return zero is they are the same node
    if node0 == node1:
        return 0

    # get the common
    mrca = tree.get_mrca_node(node0, node1)

    # store total distance
    dist = 0

    # count from each node up to mrca
    for node in (node0, node1):
        # skip if node == mrca
        if node != mrca:
            # get 1 or dist for every node up to the mrca
            if topology_only:
                dist += 1 + sum(1 for i in node._iter_ancestors(mrca))
            else:
                dist += node._dist + sum(i._dist for i in node._iter_ancestors(mrca))
    return dist


def get_node_distance_matrix(
    tree: ToyTree,
    topology_only: bool = False,
    df: bool = False
) -> Union[np.array, pd.DataFrame]:
    """Return pairwise distances between all Nodes in a ToyTree.

    Parameters
    ----------
    tree: toytree.ToyTree
        A ToyTree.
    topology_only: bool
        If True distances represent the number of edges between Nodes.
    df: bool
        If True a pandas.DataFrame is returned instead of np.ndarray.

    Returns
    -------
    node_distance_matrix: np.ndarray or pd.DataFrame
        A matrix is returned as a np.ndarray with rows and columns
        ordered by Node int idx labels, or as a pd.DataFrame with
        row and column names as str Node names for leaf Nodes and idx
        labels for internal Nodes.

    Examples
    --------
    >>> tree = toytree.rtree.unittree(10, seed=123)
    >>> toytree.distance.get_node_distance_matrix(tree)
    """
    dtype = int if topology_only else float

    # postorder ordered
    arr = np.zeros((tree.nnodes, tree.nnodes), dtype=dtype)

    # store list of descendants indices for each node
    clade_map = {}

    # reorder
    reorder = []

    # traverse tree in postorder, but first visit all tips (idxorder).
    for idx, node in enumerate(tree.traverse("postorder")):

        # init clade list to store descendants of this node
        clade_map[node] = [idx]

        # store idxorder index for re-sorting later.
        reorder.append(node.idx)

        # build desc list from children desc lists
        for child in node._children:

            # store child's clade list to parent's clade list
            clade = clade_map[child]
            clade_map[node].extend(clade)

            # set dist from child's clade members to parent
            arr[clade, idx] = arr[clade, max(clade)] + (1 if topology_only else child._dist)

        # set children clade's dists to each other
        for ch0, ch1 in itertools.combinations(node._children, 2):
            ch0 = clade_map[ch0]
            ch1 = clade_map[ch1]
            for c in ch0:
                arr[c, ch1] = arr[c, idx] + arr[ch1, idx]

    # mirror fill
    arr[np.tril_indices_from(arr)] = arr.T[np.tril_indices_from(arr)]

    # reorder into idx order
    idxorder = [reorder.index(i) for i in range(tree.nnodes)]

    # optionally format as dataframe
    if not df:
        return arr[idxorder][:, idxorder]
    index = tree.get_tip_labels() + [str(i.idx) for i in tree[tree.ntips:]]
    return pd.DataFrame(
        arr[idxorder][:, idxorder], columns=index, index=index)


def get_internal_node_distance_matrix(
    tree: ToyTree,
    topology_only: bool = False,
    df: bool = False,
) -> Union[np.array, pd.DataFrame]:
    """Return pairwise distances between non-leaf Nodes in a ToyTree.

    Parameters
    ----------
    tree: toytree.ToyTree
        A ToyTree.
    topology_only: bool
        If True distances represent the number of edges between Nodes.
    df: bool
        If True a pandas.DataFrame is returned instead of np.ndarray.

    Returns
    -------
    node_distance_matrix: np.ndarray or pd.DataFrame
        A matrix is returned as a np.ndarray with rows and columns
        ordered by Node int idx labels, or as a pd.DataFrame.

    Examples
    --------
    >>> tree = toytree.rtree.unittree(10, seed=123)
    >>> toytree.distance.get_internal_node_distance_matrix(tree)
    """
    arr = get_node_distance_matrix(tree, topology_only=topology_only, df=df)
    if not df:
        return arr[tree.ntips:, tree.ntips:]
    return arr.iloc[tree.ntips:, tree.ntips:]


def get_tip_distance_matrix(
    tree: ToyTree,
    topology_only: bool = False,
    df: bool = False
) -> Union[np.array, pd.DataFrame]:
    """Return pairwise distances between tip Nodes in a ToyTree.

    Parameters
    ----------
    tree: toytree.ToyTree
        The input ToyTree instance.
    topology_only: bool
        If True then all edges lengths are set to 1.
    df: bool
        If True a pandas.DataFrame is returned instead of np.array
        with str Node names as index and column names.

    Returns
    -------
    node_distance_matrix: np.ndarray or pd.DataFrame
        A matrix is returned as a np.ndarray with rows and columns
        ordered by Node int idx labels, or as a pd.DataFrame with
        row and column names as str Node names.

    Examples
    --------
    >>> tree = toytree.rtree.unittree(10, seed=123)
    >>> toytree.distance.get_tip_distance_matrix(tree)
    """
    arr = get_node_distance_matrix(tree, topology_only=topology_only, df=df)
    if not df:
        return arr[:tree.ntips, :tree.ntips]
    return arr.iloc[:tree.ntips, :tree.ntips]


def _get_dist_to_descendants_dict(
    tree: ToyTree,
    node: Query = None,
    topology_only: bool = False,
) -> Dict[Node, float]:
    """Return a dict {Node: distance} for Nodes at farthest distance from a selected Node.

    Distance is measured by the sum of edge lengths separating them,
    unless `topology_only` is True, in which case it is the number of
    edges separating them.

    This is used internally by other node_dist functions and is a bit
    faster than calculating the full node dist matrix when less info
    is needed.

    Example
    -------
    >>> tree = toytree.rtree.unittree(5, seed=123)
    >>> ndict = _get_dist_to_descendants_dict(tree)
    >>> # {}
    """
    # get distances among descendant nodes by traversal
    node = tree.treenode if node is None else tree.get_nodes(node)[0]
    ndists = {}
    for desc in node.traverse("preorder"):
        if desc != node:
            ndists[desc._idx] = 1 if topology_only else desc.dist
            if desc._up._idx in ndists:
                ndists[desc._idx] += ndists[desc._up._idx]
    return ndists


def get_farthest_node(
    tree: ToyTree,
    node: Query = None,
    topology_only: bool = False,
    descendants_only: bool = False,
) -> Node:
    """Return the farthest Node from a selected Node.

    Parameters
    ----------
    tree: ToyTree
        The ToyTree on which to measure Node distances.
    node: int, str, or Node
        Node in the tree selected by int idx label, str name, or Node.
    topology_only: bool
        If True distances are measured as number of edges between
        Nodes rather than by the sum of edge distances.
    descendants_only: bool
        If True then the farthest Node is only searched among the
        descendants of the 'node' query, or the root is no Node was
        selected. If False then the farthest Node is searched across
        the entire tree using `get_node_distance_matrix()`.

    Note
    ----
    If >1 Nodes are equally distance the one w/ lowest idx is returned.
    """
    # get distances to all, or only descendants
    node = tree.treenode if node is None else tree.get_nodes(node)[0]
    if descendants_only:
        ndists = _get_dist_to_descendants_dict(tree, node, topology_only)
        nidx = np.argmax(ndists.values())
    else:
        ndists = get_node_distance_matrix(tree, topology_only)
        nidx = ndists[node.idx].argmax()
    return tree[nidx]


def get_farthest_node_distance(
    tree: ToyTree,
    node: Query = None,
    topology_only: bool = False,
    descendants_only: bool = False,
) -> float:
    """Return distance to the farthest Node from a selected Node.

    Parameters
    ----------
    tree: ToyTree
        The ToyTree on which to measure Node distances.
    idx: int
        The int idx label of a Node from which to measure distances
        from. Default is None, which uses the root Node.
    topology_only: bool
        If True distances are measured as number of edges between
        two Nodes, rather than the sum of edge distances.
    descendants_only: bool
        If True then the farthest descendant Node is returned, rather
        than the farthest Node spanning any path on the tree.
    """
    node = tree.treenode if node is None else tree.get_nodes(node)[0]
    if descendants_only:
        ndists = _get_dist_to_descendants_dict(tree, node, topology_only)
        return max(ndists.values())
    return max(get_node_distance_matrix(tree, topology_only))


if __name__ == "__main__":

    import toytree
    # TREE = toytree.rtree.unittree(10, seed=123)
    # print(TREE.draw())
    # print(get_node_distance_matrix(TREE, True))

    TREE = toytree.rtree.unittree(5, seed=123)
    print(TREE.distance.get_farthest_node(5))
    print(get_node_path(TREE, 0, 5))
    TREE.treenode.draw_ascii()

    print(get_node_distance_matrix(TREE, df=True))
    print(get_tip_distance_matrix(TREE, df=True))

    tree = toytree.rtree.unittree(8, seed=123)
    ndict = _get_dist_to_descendants_dict(tree, 6)
    print(ndict)
