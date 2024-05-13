import pytest
from .fixtures import *

from fastpynuts.fastpynuts import NUTSfinder


levels = [0, 1, 2, 3]
levels_valid = [(minl_, maxl_) for minl_ in levels for maxl_ in levels if minl_ <= maxl_]
levels_invalid = [(minl_, maxl_) for minl_ in levels for maxl_ in levels if minl_ > maxl_]


# catch if min_level > max_level
@pytest.mark.parametrize("min_level, max_level", levels_invalid)
def test_wrong_level(tmp_path, min_level, max_level):
    with pytest.raises(AssertionError): NUTSfinder.from_web(scale=20, datadir=tmp_path, min_level=min_level, max_level=max_level)


# does the NUTSfinder return the expected number of regions?
@pytest.mark.parametrize("min_level,max_level", levels_valid)
def test_n_find(tmp_path, min_level, max_level, points_inside):
    nf = NUTSfinder.from_web(scale=20, datadir=tmp_path, buffer_geoms=None, min_level=min_level, max_level=max_level)
    for point in points_inside[nf.scale]: assert len(nf.find(*point)) == nf.max_level - nf.min_level + 1


@pytest.mark.parametrize("method", ["rtree"])
class TestPoints:
    # does the finder find all regions correctly?
    @pytest.mark.parametrize("point", load_random_points(scale=20, N=10, suffix="_inside"))
    def test_inside(self, nfb20, method, point): assert nfb20.find(*point, method=method) == nfb20.find(*point, method="poly")

    # does the finder correctly identify non-NUTS regions?
    @pytest.mark.parametrize("point", load_random_points(scale=20, N=1000, suffix="_outside"))
    def test_outside(self, nfb20, method, point): assert nfb20.find(*point, method=method) == []
