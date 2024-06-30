"""
Contains miscellaneous utilities.
"""

from shapely.geometry import shape
from shapely.errors import GeometryTypeError


def geometry2shapely(geometry):
    """
    Convert the geometry given by dictionary `geometry` to a `shapely` geometry using
    [shapely's `shape`](https://shapely.readthedocs.io/en/stable/manual.html#shapely.geometry.shape).
    Additionally allows to pass a GeoJSON feature containing

    Supported geometry types:
    - Polygon
    - MultiPolygon
    - MultiPoint
    - a GeoJSON feature containing one of the above valid geometries
    """
    try:
        poly = shape(geometry)
    except GeometryTypeError:
        poly = shape(geometry["geometry"])

    return poly
