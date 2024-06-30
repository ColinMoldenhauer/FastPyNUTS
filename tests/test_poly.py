import os, json
from typing import Literal

import pytest
from .fixtures import *

from fastpynuts.fastpynuts import NUTSfinder
from fastpynuts.utils import geometry2shapely


def get_geom_data(geom_name: Literal["bboxes", "geometries"]):
    """Load corresponding geometries and expected regions."""

    with open(f"tests/data/test_polys/{geom_name}_geoms.geojson") as f:
        fc = json.load(f)

    with open(f"tests/data/test_polys/{geom_name}.json") as f:
        regions = {int(key): val for key, val in json.load(f).items()}

    return fc, regions


def get_bboxes():
    """Extract bboxes from (ideally) bbox-like polygons."""
    fc, regions = get_geom_data("bboxes")
    return [(geometry2shapely(feat).bounds, regions[feat["properties"]["id"]]) for feat in fc["features"]]



def get_geoms(*geom_names):
    """Load different geometry files and their regions, and build joint feature collection."""
    fc = get_geom_data(geom_names[0])[0]
    fc["features"] = []

    regions = {}

    count = 0
    for geom_name in geom_names:
        try:
            fc_, regs_ = get_geom_data(geom_name)
        except:
            raise ValueError(f"Geometry file for type '{geom_name}' probably not present.")

        for feat in fc_["features"]:
            reg_ = regs_[feat["properties"]["id"]]

            feat["properties"]["id"] = count
            fc["features"].append(feat)

            regions[count] = reg_
            count += 1

    return [(feat, regions[feat["properties"]["id"]]) for feat in fc["features"]]



@pytest.mark.parametrize("bbox, regions_expected", get_bboxes())
def test_find_bbox(nf20, bbox, regions_expected):
    """Test `nf.find_bbox()`."""
    results = nf20.find_bbox(*bbox)
    assert sorted([hit.id for hit in results]) == sorted(regions_expected), "Wrong results using bbox geometry"


@pytest.mark.parametrize("geom, regions_expected", get_geoms("polygons", "multipolygons", "linestrings", "multipoints"))
def test_find_geoms(nf20, geom, regions_expected):
    """Test validity different kinds of intput geometry types with `nf.find_geometry()`."""

    results = nf20.find_geometry(geom)
    assert sorted([hit.id for hit in results]) == sorted(regions_expected), "Wrong results using geojson geometry"

    shapely_poly = geometry2shapely(geom)
    results = nf20.find_geometry(shapely_poly)
    assert sorted([hit.id for hit in results]) == sorted(regions_expected), "Wrong results using shapely geometry"
