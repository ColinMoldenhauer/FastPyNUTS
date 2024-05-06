import time
import re

import geojson
import numpy as np

from shapely import intersects_xy
from rtree import index
from treelib import Tree

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
    def __init__(self, geojsonfile, buffer_geoms=1e-5, min_level=0, max_level=3):
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

    @property
    def __geo_interface__(self): pass       # TODO: https://gist.github.com/sgillies/2217756


    def find(self, lon, lat, valid_point=False, **kwargs):
        """
        Find a point's NUTS regions by longitude and latitude.
        For large-scale applications, if it is known, that the point corresponds to a valid location within the NUTS regions, use `valid_point = True` for a speedup.
        """
        results = self._find_rtree(lon, lat, self.regions, valid_point=valid_point, **kwargs)
        return sorted(results)


    # Utilities
    def _parse_filename(self, file):
        scale, year, crs = re.search(r"NUTS_RG_(\d{,2})M_(\d+)_(\d+)", file).groups()
        return int(scale), int(year), int(crs)

    def _filter_regions(self, regions):
        filtered = []
        for feature in regions["features"]:
            if self.min_level <= feature["properties"]["LEVL_CODE"] <= self.max_level:
                filtered.append(feature)

        regions = [NUTSregion(feature, self.buffer) for feature in filtered]
        return regions

    def _load_regions(self):
        with open(self.file, encoding='cp850') as f:
            regions_in = geojson.load(f)

        regions_filtered = self._filter_regions(regions_in)
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


class NUTSfinderBenchmark(NUTSfinder):
    """
    Implements various methods to find corresponding NUTS regions for benchmark purposes.


    Following methods are available:

    **tree**:
    Exploits the hierarchical structure of the NUTS regions. First checks the coordinates against the NUTS level 0 regions. Then, the children regions of
    level 1 are checked, etc. At each level, region candidates are determined by a fast R-tree test, followed by a point-in-polygon check of the candidates.

    **rtree**:
    A single R-tree is constructed for all regions, independent of level. Region candidates are then determined by the R-tree's `intersect()` method,
    followed by a point-in-polygon check of the candidates.

    **bbox**:
    Sequentially performs a point-in-bbox test of all regions, followed by a point-in-polygon check of the candidates.

    **poly**:
    Sequentially performs a point-in-polygon test of all regions.
    """
    def __init__(self, geojsonfile, buffer_geoms=1e-5, min_level=0, max_level=3):
        super().__init__(geojsonfile, buffer_geoms, min_level, max_level)

        # construct additional trees
        self.tree_rtree = self._construct_tree_rtree(self.regions)
        self.tree_rtree_obj = self._construct_tree_rtree_obj(self.regions)
        self.rtree_obj = self._construct_rtree(self.regions, embed_obj=True)


    def find(self, lon, lat, method="tree", valid_point=False, verbose=False, **kwargs):
        """
        Find a point's NUTS regions by longitude and latitude.
        For large-scale applications, if it is known, that the point corresponds to a valid location within the NUTS regions, use `valid_point = True` for a speedup.
        """
        find_ = getattr(self, f"_find_{method}")
        t0 = time.time()
        results = find_(lon, lat, self.regions, valid_point=valid_point, **kwargs)
        t1 = time.time()
        if verbose: print(f"find_{method} took {t1-t0} s")
        return sorted(results)


    def _construct_tree_rtree(self, regions):
        """Construct a tree, whose nodes contain R-Tree objects. This way, the hierarchical structure of the NUTS regions can be exploited."""

        # initially construct tree
        tree = Tree()
        tree.create_node(tag="NUTS", identifier="root")
        for i, region in enumerate(regions):
            if region.level == 0:
                tree.create_node(tag=str(region), identifier=region.id, parent="root", data=region)
            else:
                parent = region.id[:-1]
                tree.create_node(tag=str(region), identifier=region.id, parent=parent, data=region)

        # construct R-tree for each node and insert into regular tree
        for node_id in tree.expand_tree():
            node = tree.get_node(node_id)
            children = tree.children(node_id)

            indices = [self.regions.index(ch.data) for ch in children]
            rtree = self._construct_rtree([ch.data for ch in children], indices=indices)
            node.data = rtree

        return tree

    def _construct_tree_rtree_obj(self, regions):
        """Like `_construct_tree_rtree`, but with negative runtime implications due to direct embedding of the region objects."""

        # initially construct tree
        tree = Tree()
        tree.create_node(tag="NUTS", identifier="root")
        for i, region in enumerate(regions):
            if region.level == 0:
                tree.create_node(tag=str(region), identifier=region.id, parent="root", data=region)
            else:
                parent = region.id[:-1]
                tree.create_node(tag=str(region), identifier=region.id, parent=parent, data=region)

        # construct R-tree for each node and insert into regular tree
        for node_id in tree.expand_tree():
            node = tree.get_node(node_id)
            children = tree.children(node_id)

            indices = [self.regions.index(ch.data) for ch in children]
            rtree = self._construct_rtree([ch.data for ch in children], indices=indices, embed_obj=True)
            node.data = rtree

        return tree


    # Finding algorithms
    def _find_poly(self, lon, lat, regions, **kwargs):
        """Naive sequential implementation, testing every region."""
        hits = []
        for region in regions:
            if intersects_xy(region.geom, lon, lat):
                hits.append(region)
        return hits

    def _find_bbox(self, lon, lat, regions, valid_point=False):
        """Bbox test."""
        hits = []
        for region in regions:
            xmin, ymin, xmax, ymax = region.bbox
            if (xmin <= lon <= xmax) and (ymin <= lat <= ymax):
                hits.append(region)
        hits = self._maybe_validate(lon, lat, hits, valid_point)

        return hits

    def _find_rtree_obj(self, lon, lat, *args, valid_point=False):
        """Find point using a R-tree. Slower variant of `_find_rtree`, due to direct embedding of objects."""

        hits = list(self.rtree_obj.intersection((lon, lat, lon, lat), objects="raw"))
        hits = self._maybe_validate(lon, lat, hits, valid_point)

        return hits

    def _find_tree(self, lon, lat, *args, valid_point=False):
        """Find point fast using a Tree-Bbox-hybrid method."""
        out = []
        current_node = "root"
        while children := self.tree.children(current_node):

            hits = self._maybe_validate(lon, lat, [ch.data for ch in children], valid_point, expected_hits=1, validation_method="_find_poly")
            out.extend(hits)

            if hits:
                current_node = hits[0].id
            else:
                if valid_point: raise ValueError(f"Could not locate point ({lon}, {lat}) despite `valid_point = True.`")
                break
        return out

    def _find_tree_rtree(self, lon, lat, *args, valid_point=False):
        """Find point fast using a Tree-Rtree-hybrid method."""
        out = []
        current_node = "root"
        while children := self.tree_rtree.children(current_node):

            rtree = self.tree_rtree[current_node].data
            hits = [self.regions[i] for i in rtree.intersection((lon, lat, lon, lat))]
            hits = self._maybe_validate(lon, lat, hits, valid_point, expected_hits=1, validation_method="_find_poly")

            out.extend(hits)
            if hits:
                current_node = hits[0].id
            else:
                if valid_point: raise ValueError(f"Could not locate point ({lon}, {lat}) despite `valid_point`=True.")
                break
        return out

    def _find_tree_rtree_obj(self, lon, lat, *args, valid_point=False):
        """Find point using a Tree-Rtree-hybrid method. Slower variant of `_find_tree_rtree`, due to direct embedding of objects."""
        out = []
        current_node = "root"
        while self.tree_rtree_obj.children(current_node):
            hits = list(self.tree_rtree_obj[current_node].data.intersection((lon, lat, lon, lat), objects="raw"))
            hits = self._maybe_validate(lon, lat, hits, valid_point, expected_hits=1, validation_method="_find_poly")

            out.extend(hits)
            if hits:
                current_node = hits[0].id
            else:
                if valid_point: raise ValueError(f"Could not locate point ({lon}, {lat}) despite `valid_point`=True.")
                break
        return out
