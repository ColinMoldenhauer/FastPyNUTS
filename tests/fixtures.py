import pytest
from .utils import load_random_points

from fastpynuts import NUTSfinder
from fastpynuts.experimental import NUTSfinderBenchmark


@pytest.fixture(scope="module")
def nf20(): return NUTSfinder.from_web(scale=20)

@pytest.fixture(scope="module")
def nfb20(): return NUTSfinderBenchmark.from_web(scale=20)

@pytest.fixture(scope="module")
def nfs(): return {scale: NUTSfinder.from_web(scale=scale) for scale in [1, 3, 10, 20, 60]}

@pytest.fixture(scope="module")
def points_inside(nfs): return {scale: load_random_points(nf.scale, N=10, suffix="_inside") for scale, nf in nfs.items()}

@pytest.fixture(scope="module")
def points_outside(nfs): return {scale: load_random_points(nf.scale, N=10, suffix="_inside") for scale, nf in nfs.items()}

@pytest.fixture(scope="module")
def finder():
    def _finder(geojson, **kwargs):
        return NUTSfinder(geojson, **kwargs)
    return _finder