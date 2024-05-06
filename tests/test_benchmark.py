import pytest
from .fixtures import *


@pytest.mark.parametrize("method", ["rtree", "rtree_obj", "tree", "tree_rtree", "tree_rtree_obj", "bbox"])
def test_methods(nfb20, method, points_inside):
    for point in points_inside[nfb20.scale]: assert nfb20.find(*point, method=method) == nfb20.find(*point, method="poly")