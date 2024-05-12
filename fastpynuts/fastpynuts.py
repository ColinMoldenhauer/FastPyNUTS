import json
import os
import re

import numpy as np

from shapely import intersects_xy
from rtree import index
from treelib import Tree

from .download import _download_NUTS
from .utils import geometry2polygon


class NUTSregion():
    """
    Hold a NUTS region's geometry and bounding box.
    """
    def __init__(self, feature, buffer=None):
        geom_type = feature["geometry"]["type"]
        assert geom_type in ["Polygon", "MultiPolygon"], f"Geometry type must be one of ['Polygon', 'MultiPolygon'], not {geom_type}"
        assert feature["id"] == feature["properties"]["NUTS_ID"]

        self.feature = feature
        self.buffer = buffer
        self.coordinates = feature["geometry"]["coordinates"]

        self.geom = geometry2polygon(feature)
        if buffer: self.geom = self.geom.buffer(buffer)

        self.bbox = self.geom.bounds
        self.properties = feature["properties"]


    def __str__(self): return f"NUTS{self.level}: {self.id}"

    def __repr__(self): return str(self)

    def __eq__(self, other): return self.id == other.id

    def __lt__(self, other): return (self.level < other.level) or (self.level == other.level and self.id < other.id)


    @property
    def id(self): return self.properties["NUTS_ID"]

    @property
    def level(self): return self.properties["LEVL_CODE"]

    @property
    def type(self): return self.feature["type"]

    @property
    def is_multi(self): return self.type == "MultiPolygon"

    @property
    def __geo_interface__(self): return self.feature


class NUTSfinder:
    """
    Find NUTS regions for a point coordinate `(lon, lat)`. Optionally restrict the NUTS levels of interest.

    **Note**: Points-in-polyon tests via `shapely` may suffer from floating-point precision issues for points on the boundary of regions.
    A buffer to the regions may be introduced via the `buffer_geoms` keyword to ensure the correct assignment. On the flip-side,
    a buffer may lead to the assignment of multiple regions for points on the boundary.
    """
    def __init__(self, geojsonfile, buffer_geoms=0, min_level=0, max_level=3):
        assert min_level <= max_level, "`min_level` <= `max_level'"
        self.min_level = min_level
        self.max_level = max_level

        self.file = geojsonfile
        self.buffer = buffer_geoms

        self.scale, self.year, self.crs = self._parse_filename(geojsonfile)
        self.regions = self._load_regions()
        self.tree = self._construct_tree(self.regions)

        self.rtree = self._construct_rtree(self.regions)

    def __getitem__(self, idx): return self.regions[idx]

    def __len__(self): return len(self.regions)


    @classmethod
    def from_web(cls, scale=1, year=2021, epsg=4326, datadir=".data", **kwargs):
        """
        Download a NUTS file from Eurostat and construct a `NUTSfinder` object from it. If previously downloaded, use existing file instead.
        By default, the file will be saved in `.data`. The download location can be changed via the `datadir` keyword.
        The construction of the finder object can be specified via `kwargs`. For available keyword arguments, see the documentation of `NUTSfinder`.
        """
        os.makedirs(datadir, exist_ok=True)
        file = os.path.join(datadir, f"NUTS_RG_{scale:02d}M_{year}_{epsg}.geojson")

        if os.path.exists(file):
            return cls(file)
        else:
            return cls(_download_NUTS(datadir, scale=scale, year=year, epsg=epsg), **kwargs)


    def find(self, lon, lat, valid_point=False, **kwargs):
        """
        Find a point's NUTS regions by longitude and latitude.
        For large-scale applications, if it is known, that the point corresponds to a valid location within the NUTS regions, use `valid_point = True` for a speedup.
        """
        results = self._find_rtree(lon, lat, self.regions, valid_point=valid_point)
        return sorted(results)

    def find_level(self, lon, lat, level, valid_point=False):
        """
        Find specific NUTS levels. `level` may either be an integer or iterable of integers.
        """
        if isinstance(level, int): level = [level]
        assert all([self.min_level <= level_ <= self.max_level for level_ in level]), "All specified levels must be between self.min_level and self.max_level."

        results_all = self.find(lon, lat, valid_point=valid_point)
        return [result for result in results_all if result.level in level]



    # Utilities
    def _parse_filename(self, file):
        scale, year, crs = re.search(r"NUTS_RG_(\d{,2})M_(\d+)_(\d+)", file).groups()
        return int(scale), int(year), int(crs)

    def _filter_regions(self, fc):
        filtered = []
        for feature in fc["features"]:
            if self.min_level <= feature["properties"]["LEVL_CODE"] <= self.max_level:
                filtered.append(feature)

        regions = [NUTSregion(feature, self.buffer) for feature in filtered]
        return regions

    def _load_regions(self):
        with open(self.file, encoding='cp850') as f:
            fc = json.load(f)

        regions_filtered = self._filter_regions(fc)
        return sorted(regions_filtered)

    def _construct_rtree(self, regions, indices=None, embed_obj=False):
        """
        Construct a fast R-tree based on the regions' bounding boxes.

        Indices should refer to the indices of the region objects in `self.regions`. They will be used to retrieve
        the region objects from the indices returned by `rtree.index.Index.intersection()`.

        Optionally embed the region objects in the rtree nodes. This has negative runtime implications.
        """
        idx = index.Index()
        for i, region in zip(indices or range(len(regions)), regions):
            if embed_obj:
                idx.insert(id=i, coordinates=region.bbox, obj=region)
            else:
                idx.insert(id=i, coordinates=region.bbox)
        return idx

    def _construct_tree(self, regions):
        """Construct a tree, whose nodes contain NUTSregion objects. This way, the hierarchical structure of the NUTS regions can be exploited."""

        tree = Tree()
        tree.create_node(tag="NUTS", identifier="root")
        for i, region in enumerate(regions):
            if region.level == self.min_level:
                tree.create_node(tag=str(region), identifier=region.id, parent="root", data=region)
            else:
                parent = region.id[:-1]
                tree.create_node(tag=str(region), identifier=region.id, parent=parent, data=region)

        return tree

    def _get_parents(self, id):
        """Get the parent regions of a region from `self.tree`."""
        parents = []
        current_id = id
        while parent_region := self.tree.parent(current_id).data:
            parents.append(parent_region)
            current_id = parent_region.id
        return parents


    # finding utilities
    def _find_rtree(self, lon, lat, *args, valid_point=False):
        """Find point fast using a R-tree."""
        hits = self._candidates_rtree(lon, lat, self.regions)
        hits = self._maybe_validate(lon, lat, hits, valid_point)
        return hits

    def _candidates_rtree(self, lon, lat, regions):
        """Determine the candidate regions by R-tree intersection."""
        hits = [regions[i] for i in self.rtree.intersection((lon, lat, lon, lat))]
        return hits

    def _maybe_validate(self, lon, lat, hits, valid_point, expected_hits=None, validation_method="_validate_candidate_set"):
        """
        A-priori knowledge about the validity of query points can be used to maximize the querying speed.

        If it can be assumed, that the point is inside a NUTS region, final validity checks can be skipped if the correct number of regions is present in `hits`.
        If validity can not be assumed, a final point-in-polygon test is necessary.
        """
        expected_hits = expected_hits or self.max_level-self.min_level+1

        validate = getattr(self, validation_method)

        if valid_point and len(hits) == expected_hits:
            return hits
        else:
            return validate(lon, lat, hits)

    def _validate_candidate_set(self, lon, lat, hits):
        """
        In case of bbox candidate selection, wrong candidates with overlapping bbboxes may be suggested. For NUTS,
        we expect all parent regions to be included in the candidate set. If the parent regions are missing, we can safely discard
        regions and avoid an unnecessary point-in-polyon test. If no buffer is used, at max one full set of regions can be found.
        If a buffer is applied to the regions, boundary points might coincide with multiple regions.
        """

        max_levels = [hit for hit in hits if hit.level == self.max_level]
        validated = []
        for region in max_levels:
            parents = self._get_parents(region.id)
            if all([p in hits for p in parents]) and intersects_xy(region.geom, lon, lat):
                validated.extend([*parents, region])
                if not self.buffer: return validated

        validated = np.unique(validated).tolist()
        return validated
