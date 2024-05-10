import pytest

from fastpynuts.download import _get_NUTS_url

@pytest.mark.parametrize("input, expected", [

    # check default
    [{}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326.geojson"],

    # check geomtypes
    [{"geomtype": "BN"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_BN_01M_2021_4326.geojson"],
    [{"geomtype": "RG"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326.geojson"],
    [{"geomtype": "LB"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_LB_01M_2021_4326.geojson"],

    # check scales
    [{"scale": 20}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2021_4326.geojson"],
    [{"scale": 60}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_60M_2021_4326.geojson"],

    # check years
    [{"year": 2010}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2010_4326.geojson"],
    [{"year": 2006}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2006_4326.geojson"],

    # check formats
    [{"format": "pbf"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/pbf/NUTS_RG_01M_2021_4326.pbf"],
    [{"format": "shp"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/shp/NUTS_RG_01M_2021_4326.shp"],
    [{"format": "svg"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/svg/NUTS_RG_01M_2021_4326.svg"],
    [{"format": "topojson"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/topojson/NUTS_RG_01M_2021_4326.json"],

    # check epsg
    [{"epsg": 3035}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_3035.geojson"],
    [{"epsg": 3857}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_3857.geojson"],

    # check level
    [{"level": 0}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326_LEVL_0.geojson"],

    # case invariance
    [{"geomtype": "rg"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326.geojson"],
    [{"format": "GEOJSON"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326.geojson"],
    [{"format": "GeoJSON"}, "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326.geojson"],
])
def test_urls(input, expected):
    assert _get_NUTS_url(**input)[1] == expected

@pytest.mark.parametrize("input", [
    {"geomtype": "some_type"},
    {"scale": 2},
    {"scale": 1.3},
    {"year": 1999},
    {"format": "csv"},
    {"format": "json"},
    {"format": "some_format"},
    {"epsg": 3036},
    {"level": 6},
    {"level": -1},
])
def test_wrong_parameters(input):
    with pytest.raises(AssertionError):
        _get_NUTS_url(**input)
