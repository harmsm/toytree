#!/usr/bin/env python

"""Canvas setup functions for single or grids of trees."""


# from typing import Tuple
import numpy as np
# from toytree.core import


# def get_linear_width_and_height(mark: MultiTreeMark) -> Tuple[int, int]:
#     """Return height and width for tree grid if not set by user."""
#     if mark.layout in "du":
#         minx = 225
#         miny = 250
#         width = mark.width if mark.width else min(750, minx * mark.ncols)
#         height = mark.height if mark.height else min(750, miny * mark.nrows)
#         return width, height

#     minx = 250
#     miny = 225
#     height = mark.height if mark.height else min(750, minx * mark.nrows)
#     width = mark.width if mark.width else min(750, miny * mark.ncols)
#     return width, height


# @dataclass
# class Grid:
#     nrows: int
#     ncols: int
#     width: int
#     height: int
#     layout: str
#     margin: int
#     padding: int
#     scale_bar: bool

#     # attrs to be filled 
#     canvas: toyplot.Canvas = None
#     axes: toyplot.coordinates.Cartesian = None

#     def get_axes(self) -> None:
#         ...

#     def get_canvas(self) -> None:
#         ...


# def get_canvas_and_axes(...) -> ...:
#     ...


class GridSetup:
    """Return Canvas and Cartesian axes objects to fit a grid of trees."""

    def __init__(
        self,
        nrows,
        ncols,
        width,
        height,
        layout,
        margin,
        padding,
        scale_bar,
    ):

        # style args can include height/width, nrows, ncols, shared,...
        self.nrows = nrows
        self.ncols = ncols
        self.width = width
        self.height = height
        self.layout = layout
        self.margin = margin
        self.padding = padding
        self.scale_bar = scale_bar

        # get .canvas and .axes
        self.get_tree_dims()
        self.canvas = toyplot.Canvas(
            height=self.height,
            width=self.width,
        )
        self.axes = []
        self.get_axes()
        # self.get_axes_list()

    def get_axes(self):
        """
        Get a list of axes in the grid shape, and set margins to
        to make space for optional scale_bars and axes labels.
        """
        nplots = self.nrows * self.ncols
        grid = np.arange(nplots).reshape((self.nrows, self.ncols))

        for idx in range(nplots):
            if self.margin:
                margin = self.margin
            else:
                if self.nrows == 1:
                    margin = [50, 10, 50, 30]
                    # else:
                    # margin = [50, 20, 50, 20]
                else:
                    margin = [30, 30, 30, 30]
                    row, _ = np.where(grid == idx)
                    if row == 0:
                        margin[0] += 10
                        margin[2] -= 10
                    if row == self.nrows - 1:
                        margin[2] += 10
                        margin[0] -= 10
                # ...
                if self.scale_bar:
                    if self.layout in "du":
                        margin[3] += 20
                    elif self.layout in "lr":
                        margin[2] += 20
                margin = tuple(margin)

            axes = self.canvas.cartesian(
                grid=(self.nrows, self.ncols, idx),
                padding=self.padding,
                margin=margin,
            )
            axes.margin = margin
            self.axes.append(axes)

    def get_tree_dims(self):
        """
        get height and width if not set by user
        """
        # wider than tall
        if self.layout in ("d", "u"):
            minx = 225
            miny = 250
            self.width = self.width if self.width else min(750, minx * self.ncols)
            self.height = self.height if self.height else min(750, miny * self.nrows)

        else:
            minx = 250
            miny = 225
            self.height = self.height if self.height else min(750, minx * self.nrows)
            self.width = self.width if self.width else min(750, miny * self.ncols)


if __name__ == "__main__":

    # get_multitree_grid()

    pass
    # canvas_