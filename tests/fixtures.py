import pytest
from .utils import get_available_NUTS_files, load_random_points

from fastpynuts import NUTSfinder
from fastpynuts.experimental import NUTSfinderBenchmark


@pytest.fixture(scope="module")
def f20(): return get_available_NUTS_files(scale="20")[0]

@pytest.fixture(scope="module")
def nf20(f20): return NUTSfinder(f20)

@pytest.fixture(scope="module")
def nfb20(f20): return NUTSfinderBenchmark(f20)

@pytest.fixture(scope="module")
def nfs(): return {scale: NUTSfinder(get_available_NUTS_files(scale=scale, year=2021, epsg=4326)[0]) for scale in [1, 3, 10, 20, 60]}

@pytest.fixture(scope="module")
def points_inside(nfs): return {scale: load_random_points(nf.scale, N=10, suffix="_inside") for scale, nf in nfs.items()}

@pytest.fixture(scope="module")
def points_outside(nfs): return {scale: load_random_points(nf.scale, N=10, suffix="_inside") for scale, nf in nfs.items()}

@pytest.fixture(scope="module")
def finder():

    def _finder(geojson, **kwargs):
        return NUTSfinder(geojson, **kwargs)

    return _finder