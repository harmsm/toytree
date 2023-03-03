#!/usr/bin/env python

"""...

"""


import unittest
import numpy as np
import toyplot
import toytree
from toytree.style import TreeStyle, validate_style
from toytree.style.src.validator import get_color_mapped_feature
from toytree.utils import ToytreeError


class TestValidator(unittest.TestCase):
    def setUp(self):

        self.itree = toytree.rtree.imbtree(10, seed=123, treeheight=10)
        self.btree = toytree.rtree.baltree(10, seed=123, treeheight=10)
        self.utree = toytree.rtree.unittree(10, seed=123, treeheight=10)
        self.trees = [self.itree, self.btree, self.utree]

    def test_node_colormap_style_repr_before_validation(self):
        """Set node colormap on style dict and show repr (json) w/o error."""
        tree = self.itree
        colors = [
            ("dist", "BlueRed"),
            ("dist", toyplot.color.brewer.map("BlueRed")),
            toytree.color.ToyColor((0, 1, 0, 0.5)),
            (0, 1, 0.5, 0.5),
            "red",
            ["blue"] + ["red"] * (tree.nnodes - 1),
        ]
        for color_arg in colors:
            tree.style.node_colors = color_arg
            tree.style.json()

    def test_node_colormap_support_nan(self):
        """Set nan values to transparent when color mapping."""
        # set data with missing values on some nodes
        svals = {11: 0, 12: 50, 13: 75, 14: 100}
        tree = self.itree.set_node_data("support", svals)
        vals = tree.get_node_data("support").values

        # create a color map
        cmap = toyplot.color.brewer.map("BlueRed")
        cmap.domain.max = 0
        cmap.domain.max = 10

        # call internal color mapping func used by validator for (feat, cmap)
        colors = get_color_mapped_feature(vals, cmap)

        # assert nans were converted to transparent
        pre = np.where(np.isnan(vals))
        post = np.where(colors == toytree.color.ToyColor("transparent"))
        self.assertEqual(list(pre[0]), list(post[0]))

        # assert no min max domain on colormap gets autosettings.
        # ...

    def test_node_style_opacity_overrule(self):
        """... opacity should overrule orig fill color opacity."""
        tree = self.itree
        tree.style.node_colors = ['red'] + ['blue'] * (tree.nnodes - 1)
        tree.style.node_style.fill_opacity = 0.2
        style = tree.style.copy()
        validate_style(tree, style)
        # print(style.node_colors)

        tree.style.node_colors = ("dist", "BlueRed")
        tree.style.node_style.fill_opacity = 0.2
        # self.assertEqual()        

    def test_edge_style_opacity_overrule(self):
        """..."""
        tree = self.itree
        tree.style.edge_colors = ['red'] + ['blue'] * (tree.nnodes - 1)
        tree.style.edge_style.stroke_opacity = 0.2
        style = tree.style.copy()
        # validate_style(tree, style)
        # print(style.node_colors)

    def test_set_nan_node_labels_empty_string(self):
        """np.nan values on node labels should validate to empty strings."""
        self.itree.style.node_colors = "red"
        # style = self.itree.style._validate()
        # self.assertEqual(style, dict...)

    # def test_node_size_to_zeros_for_empty_labels(self):
    #     """Do this?"""

    def test_node_labels_round_floats_on_validate(self):
        """..."""
        self.btree.treenode.children[0].support = 99.99
        self.btree.treenode.children[1].support = 10


    def test_anchor_shift_legacy_support(self):
        """Support -toyplot-anchor-shift as legacy to anchor-shift."""

        # assert warning message is reported on -toyplot-anchor-shift


        # assert tip_labels support for anchor-shift


        # assert node_labels support for anchor-shift


if __name__ == "__main__":

    unittest.main()
