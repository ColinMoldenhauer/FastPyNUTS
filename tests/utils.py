import glob
import json

from fastpynuts import NUTSfinder


def get_available_NUTS_files(scale=None, year=None, epsg=None, datadir="tests/data"):
    if isinstance(scale, int): scale = f"{scale:02d}"
    scale_ = scale if scale is not None else '[0-9]*'
    year_ = year if year is not None else '[0-9]*'
    epsg_ = epsg if epsg is not None else '[0-9]*'
    files = glob.glob(pattern := f"{datadir}/NUTS_RG_{scale_}M_{year_}_{epsg_}.geojson")
    return files


def get_regions(scale="20", year=2021, epsg=4326, datadir="tests/data"):
    nf = NUTSfinder(get_available_NUTS_files(scale, year, epsg, datadir)[0])
    return nf.regions

def load_random_points(scale, suffix="_inside", N=1, testdatadir="tests/data"):
    with open(f"{testdatadir}/benchmark_points_{N}_scale_{scale}{suffix}.geojson") as f:
        fc = json.load(f)
        points = [feature["geometry"]["coordinates"] for feature in fc["features"]]
    return points