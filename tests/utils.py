import json
import tempfile

from fastpynuts.fastpynuts import NUTSfinder


def get_regions(**kwargs):
    tmp_dir = tempfile.TemporaryDirectory()
    regions = NUTSfinder.from_web(datadir=tmp_dir.name, **kwargs).regions
    return regions

def load_random_points(scale, suffix="_inside", N=1, testdatadir="tests/data"):
    with open(f"{testdatadir}/benchmark_points_{N}_scale_{scale}{suffix}.geojson") as f:
        fc = json.load(f)
        points = [feature["geometry"]["coordinates"] for feature in fc["features"]]
    return points