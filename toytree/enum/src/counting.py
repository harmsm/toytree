#!/usr/bin/env python

"""Enumeration counting module.

This module implements mathematical operations related to counting
numbers of trees and metrics related to tree space.

Authors
-------
Deren Eaton and Carlos Alonso Maya-Lastra

TODO
----
- should all funcs take int|ToyTree as input and be exposed to Tree API?
- check and explain n labeled/unlabeld versus rooted/unrooted trees.

References
----------
- Edwards AWF (1970). Estimation of the branch points of a branching diffusion process. J. R. Stat. Soc. Ser. B 32:155-174
- Harding EF (1971) The probabilities of rooted tree-shapes generated by random bifurcation. Adv Appl Prob 3: 44–77.
Harding provides recursive formula for hte probabilities of labeled and unlabeled topologies. See Brown for full solutions.
- Brown JKM (1994) Probabilities of evolutionary trees. Syst Biol 43: 78–91.
Brown developed probability calculations for all labeled and unlabeled topologies by developing expressions for the number of ways that internal nodes can be arranged relative to one another in time.
- Aldous DJ (2001) Stochastic models and descriptive statistics for phylogenetic trees, from Yule to today. Stat Sci 16: 23–34.
- Steel M, McKenzie A (2001) Properties of phylogenetic trees generated by Yule-type speciation models. Math Biosci 170: 91–112.
- Pamilo and Nei (1988) ...
"""

from math import prod, factorial
from scipy.special import comb as scipy_comb
from toytree.core import ToyTree
from toytree.core.apis import TreeEnumAPI, add_subpackage_method


__all__ = [
    "get_num_bifurcating_trees",     # Module
    "get_num_quartets",              # Module and Tree API
    "get_num_subtrees",              # Module and Tree API
    "get_num_labeled_trees",         # Module
    # "get_num_unlabeled_trees",
    # "iter_labeled_trees",    # moved to enum/topologies
    # "iter_unlabeled_trees",  # moved to enum/topologies
]


# -------------------------------------------------------------------
# -------------------------------------------------------------------
# Didactic functions used in lessons. See `get_num_bifurcating_trees`
# as the recommended faster option for counting.
def _get_num_places_a_tip_can_be_added(ntips: int, rooted: bool = True) -> int:
    """Return num places a tip can be added to a bifurcating rooted
    or unrooted tree.

    Rooted = `2 * (ntips + 1) - 3`.
    Unrooted = `2 * (ntips + 1) - 5`
    """
    if not rooted:
        return 2 * (ntips + 1) - 5
    return 2 * (ntips + 1) - 3


# This is didactic, not as fast as get_num_bifurcating_rooted_trees()
# but also not that much slower.
def _get_num_bifurcating_trees_by_successive_odds(ntips: int, rooted: bool = True) -> int:
    """Return number of rooted trees

    As discussed in Felsenstein (2004), there are a couple of ways to
    get the possible number of bifurcating rooted trees considering
    the places where a n-tip can be added. Considering one of the
    methods mentioned, we can create a list of successive odds
    (places where a new tip can be added) and use it to get the
    number of possible tips.
    """
    # To save list of successive odd integers
    successive_odds = (
        _get_num_places_a_tip_can_be_added(i, rooted=rooted)
        for i in range(2, ntips)
    )
    return prod(successive_odds)
# -------------------------------------------------------------------
# -------------------------------------------------------------------


def get_num_bifurcating_trees(ntips: int, rooted: bool = True) -> int:
    """Return number of bifurcating trees for ntips (leaf nodes) as
    rooted or unrooted trees.

    Equations
    ---------
    Rooted = (2x-3)! / (2**(x-2) (x-3)!)
    Unrooted = (2 (x-1) -3)! / (2**[x-3] (x-3)!)

    Parameters
    ----------
    ntips: int
        The number of tips.
    rooted: bool
        If True the equation for counting rooted trees is used else
        the equation for unrooted trees. There are always more possible
        rooted trees than unrooted trees.
    """
    # rooted case
    if rooted:
        ntrees = int(
            factorial(2 * ntips - 3)
            / (2 ** (ntips - 2) * factorial(ntips - 2))
        )
    # unrooted case
    else:
        ntrees = int(
            factorial(2 * (ntips - 1) - 3)
            / (2 ** (ntips - 3) * factorial(ntips - 3))
        )
    return ntrees


@add_subpackage_method(TreeEnumAPI)
def get_num_quartets(ntips: int | ToyTree, method: int = 0) -> int:
    """Return number of possible quartet trees (ntips=4) that can be
    extracted from a larger tree of size ntips.

    This uses the formula for binomial coefficient.

    Parameters
    ----------
    ntips: int
        The number of tips in the full tree.

    Note
    ----
    This is a special case of the `enum.get_num_subtrees` function
    which can calculate the number of subtrees of size >4.
    """
    # input can be int or a ToyTree from which ntips is extracted
    ntips = ntips if isinstance(ntips, int) else ntips.ntips

    # fastest method tested
    return scipy_comb(ntips, 4, exact=True)


@add_subpackage_method(TreeEnumAPI)
def get_num_subtrees(ntips: int | ToyTree, subtree_size: int) -> int:
    """Return number of possible subtrees of subtree_size tips that
    can be extracted from a larger tree of size ntips.

    This uses the formula for binomial coefficient.

    Parameters
    ----------
    ntips: int
        The number of tips in the full tree.
    subtree_size: int
        The number of tips in the subtrees (subtree size).
    """
    # input can be int or a ToyTree from which ntips is extracted
    ntips = ntips if isinstance(ntips, int) else ntips.ntips

    # fastest method tested
    return scipy_comb(ntips, subtree_size, exact=True)


def get_num_labeled_trees(ntips: int) -> int:
    r"""Return the number of possible labeled trees for ntips.

    Note
    ----
    The term "labeled trees" has a specific meaning when discussing
    tree space. According to Harding (1971): 
    "At each node, the descendant species are partitioned
    into two subtrees. A node at which the subtrees have identical 
    unlabeled topologies is balanced; otherwise, it is unbalanced."
    In other words, balanced cherries on a rooted tree contribute
    differently than unbalanced nodes to quantifying labeled trees.

    $$ H_n = \frac{n!(n - 1)!}{2^{n - 1}} $$

    ---------------------------
    | ntips | n labeled trees |
    |-------|-----------------|
    |   3   |        3        |
    |   4   |       18        |
    |   5   |      180        |
    |   6   |     2700        |
    | ...   |      ...        |
    |-------|-----------------|

    See Also
    --------
    ...

    Note
    ----
    Labeled trees

    References
    ----------
    - Edwards (1970)
    - Harding EF (1971) The probabilities of rooted tree-shapes generated by random bifurcation. Adv Appl Prob 3: 44–77.
    - Brown JKM (1994) Probabilities of evolutionary trees. Syst Biol 43: 78–91.
    """
    ntrees = int(
        (factorial(ntips) * factorial(ntips - 1))
        / (2 ** (ntips - 1))
    )
    return ntrees


def get_num_unlabeled_trees(ntips: int) -> int:
    r"""...

    See Harding...

    Note
    ----
    In contrast to labeled trees, all unlabeled trees for ntips are
    *not* equiprobable.
    """



if __name__ == "__main__":

    # get_probability_gene_tree_matches_species_tree(0.001)
    # print(get_num_labeled_trees(6))
    print(get_num_quartets(10, 4))
