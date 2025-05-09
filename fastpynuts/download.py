"""
Contains utilities for the automatic download of NUTS files.
"""

import os
import urllib.request


def get_NUTS_url(geomtype="RG", scale=1, year=2021, format="geojson", epsg=4326, level=None):
    """
    Create the URL to a NUTS file in the Eurostat API.
    For a specification of the parameters, see https://gisco-services.ec.europa.eu/distribution/v2/nuts/nuts-2021-files.html
    Download of CSV is not supported due to different signature.
    """
    geomtype = geomtype.upper()
    format = format.lower()

    assert geomtype in {"RG", "BN", "LB"}
    assert scale in {1, 3, 10, 20, 60}
    assert year in {2024, 2021, 2016, 2013, 2010, 2006, 2003}
    assert format in {"geojson", "pbf", "shp", "svg", "topojson"}
    assert epsg in {4326, 3035, 3857}
    if level is not None: assert level in {0, 1, 2, 3}

    base_url = r"https://gisco-services.ec.europa.eu/distribution/v2/nuts"

    suffix = f"_LEVL_{level}" if level is not None else ""
    filename = f"NUTS_{geomtype}_{scale:02d}M_{year}_{epsg}{suffix}.{format if format != 'topojson' else 'json'}"
    url = f"{base_url}/{format}/{filename}"

    return filename, url


def download_NUTS(datadir=None, filename=None, scale=1, year=2021, epsg=4326, level=None):
    """
    Download a NUTS file from the Eurostat API and save to file.
    """
    assert bool(datadir) ^ bool(filename), "Specify exactly one of datadir or filename"
    filename_NUTS, url = get_NUTS_url(scale=scale, year=year, epsg=epsg, level=level)
    with urllib.request.urlopen(url) as resp:
        with open(file := os.path.join(datadir, filename or filename_NUTS), "wb") as f:
            f.write(resp.read())
    return file
