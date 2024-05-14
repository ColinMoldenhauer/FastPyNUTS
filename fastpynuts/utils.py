"""
Contains miscellaneous utilities.
"""

from shapely.geometry import Polygon, MultiPolygon, MultiPoint


def geometry2polygon(feature):
    """
    Convert the geometry given by dictionary `feature` to a `shapely` geometry.
    """
    geometry = feature["geometry"]
    if geometry["type"]=="Polygon":
        poly = Polygon(geometry["coordinates"][0], holes=geometry["coordinates"][1:])
    elif geometry["type"]=="MultiPolygon":
        poly = MultiPolygon([Polygon(coord[0], holes=coord[1:]) for coord in geometry["coordinates"]])
    elif geometry["type"]=="MultiPoint":
        poly = MultiPoint(geometry["coordinates"])
    else:
        raise NotImplementedError(f'geometry2polygon: type {geometry["type"]} not supported yet!')
    return poly
