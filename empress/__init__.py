"""
Wraps empress functionalities
"""
import matplotlib
# the tkagg backend is for pop-up windows, and will not work in environments
# without graphics such as a remote server. Refer to issue #49
try: 
    matplotlib.use("tkagg")
except ImportError:
    print("Using Agg backend: will not be able to create pop-up windows.")
    matplotlib.use("Agg")
from matplotlib import pyplot as plt
from typing import List, Iterable
from abc import ABC, abstractmethod

from empress.xscape.CostVector import CostVector
from empress import newickFormatReader
from empress.newickFormatReader import ReconInput
from empress.newickFormatReader import getInput as read_input
from empress.xscape.reconcile import reconcile as xscape_reconcile
from empress.xscape.plotcostsAnalytic import plot_costs_on_axis as xscape_plot_costs_on_axis


class Drawable(ABC):
    """
    Implements a default draw method
    """

    @abstractmethod
    def draw_on(self, axes: plt.Axes):
        """
        Draw self on matplotlib Axes
        """
        pass

    def draw(self) -> plt.Figure:
        """
        Draw self as matplotlib Figure.
        """
        figure, ax = plt.subplots(1, 1)
        self.draw_on(ax)
        return figure

    def draw_to_file(self, fname):
        """
        Draw self and save it as image at path fname.
        """
        figure = self.draw()
        figure.savefig(fname)


class ReconciliationWrapper(Drawable):
    # TODO: Replace dict with Reconciliation type
    # https://github.com/ssantichaivekin/eMPRess/issues/30
    def __init__(self, reconciliation: dict):
        self._reconciliation = reconciliation

    def draw_on(self, axes: plt.Axes):
        pass


class ReconGraphWrapper(Drawable):
    # TODO: Replace dict with ReconGraph type
    # https://github.com/ssantichaivekin/eMPRess/issues/30
    def __init__(self, recongraph: dict):
        self._recongraph = recongraph

    def find_median(self) -> ReconciliationWrapper:
        """
        Find and return one median of self
        """
        pass

    def draw_on(self, axes: plt.Axes):
        pass

    def cluster(self, n) -> List['ReconGraphWrapper']:
        """
        Cluster self into n reconciliation graphs
        """
        pass


class CostRegionsWrapper(Drawable):
    def __init__(self, cost_vectors, transfer_min, transfer_max, dup_min, dup_max):
        """
        CostRegionsWrapper wraps all information required to display a cost region plot.
        """
        self._cost_vectors = cost_vectors
        self._transfer_min = transfer_min
        self._transfer_max = transfer_max
        self._dup_min = dup_min
        self._dup_max = dup_max

    def draw_on(self, axes: plt.Axes, log=False):
        xscape_plot_costs_on_axis(axes, self._cost_vectors, self._transfer_min, self._transfer_max,
                                  self._dup_min, self._dup_max, log=False)


def compute_cost_regions(recon_input: ReconInput, transfer_min: float, transfer_max: float,
                         dup_min: float, dup_max: float) -> CostRegionsWrapper:
    """
    Compute the cost polygon of recon_input. The cost polygon can be used
    to create a figure that separate costs into different regions.
    """
    parasite_tree = recon_input.parasite_tree
    host_tree = recon_input.host_tree
    tip_mapping = recon_input.phi
    cost_vectors = xscape_reconcile(parasite_tree, host_tree, tip_mapping, transfer_min, transfer_max, dup_min, dup_max)
    return CostRegionsWrapper(cost_vectors, transfer_min, transfer_max, dup_min, dup_max)


def reconcile(recon_input: ReconInput, dup_cost: int, trans_cost: int, loss_cost: int) -> ReconGraphWrapper:
    """
    Given recon_input (which has parasite tree, host tree, and tip mapping info)
    and the cost of the three events, computes and returns a reconciliation graph.
    """
    pass
