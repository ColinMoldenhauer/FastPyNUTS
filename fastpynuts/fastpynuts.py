import time
import re

import geojson
import numpy as np

from shapely.geometry import Point, Polygon
from rtree import index
from treelib import Tree
from treelib.exceptions import NodeIDAbsentError

from .utils import geometry2polygon



class NUTSregion():
    # TODO: evaluate impact of redundancy of information
    def __init__(self, feature):
        geom_type = feature["geometry"]["type"]
        assert geom_type in ["Polygon", "MultiPolygon"], f"Geometry type must be one of ['Polygon', 'MultiPolygon'], not {geom_type}"
        assert feature["id"] == feature["properties"]["NUTS_ID"]

        self.feature = feature
        self.coordinates = feature["geometry"]["coordinates"]               # list
        self.geom = geometry2polygon(feature)                               # shapely geometry
        self.bbox = self.geom.bounds                                        # tuple
        self.properties = feature["properties"]                             # dict


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
    # TODO: make geojsonfile optional -> download and caching
    def __init__(self, geojsonfile, level=None, min_level=0, max_level=3):
        self.file = geojsonfile

        self.scale, self.year, self.crs = self._parse_filename(geojsonfile)
        self.regions = self._load_regions(level, min_level, max_level)                 # store initial regions for dynamic filtering (avoid reloading large input files for new filters)

        self.rtree = self._construct_rtree(self.regions)
        self.rtree_obj = self._construct_rtree(self.regions, embed_obj=True)

        self.tree = self._construct_tree(self.regions)
        self.tree_rtree = self._construct_tree_rtree(self.regions)
        self.tree_rtree_obj = self._construct_tree_rtree_obj(self.regions)

    def __getitem__(self, idx): return self.regions[idx]

    def __len__(self): return len(self.regions)


    def find(self, lon, lat, method="tree", valid_point=False, verbose=False, **kwargs):
        """
        Find a point's NUTS regions by longitude and latitude.
        For large-scale applications, if it is known, that the point corresponds to a valid location within the NUTS regions, use `valid_point = True` for a speedup.


        Multiple methods are available:

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
        find_ = getattr(self, f"_find_{method}")
        t0 = time.time()
        results = find_(lon, lat, self.regions, valid_point=valid_point, **kwargs)
        t1 = time.time()
        if verbose: print(f"find_{method} took {t1-t0} s")
        return sorted(results)


    # Utilities
    def _parse_filename(self, file):
        scale, year, crs = re.search("NUTS_RG_(\d{,2})M_(\d+)_(\d+)", file).groups()
        return int(scale), int(year), int(crs)

    def _set_level(self, level=None, min_level=0, max_level=3):
        if level:
            self.min_level = level
            self.max_level = level
        else:
            self.min_level = min_level
            self.max_level = max_level

    def _filter_regions(self, regions):
        filtered = []
        for feature in regions["features"]:
            if self.min_level <= feature["properties"]["LEVL_CODE"] <= self.max_level:
                filtered.append(feature)

        regions = [NUTSregion(feature) for feature in filtered]
        return regions

    def _load_regions(self, level=None, min_level=0, max_level=3):
        with open(self.file, encoding='cp850') as f:
            regions_in = geojson.load(f)

        self._set_level(level, min_level, max_level)
        regions_filtered = self._filter_regions(regions_in)

        return sorted(regions_filtered)


    # constructing trees
    def _construct_rtree(self, regions, indices=None, embed_obj=False):
        """
        Construct a fast R-tree based on the regions' bounding boxes.

        Indices should refer to the indices of the region objects in `self.regions`. Will be used to retreive
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
            if region.level == 0:
                tree.create_node(tag=str(region), identifier=region.id, parent="root", data=region)
            else:
                parent = region.id[:-1]
                try:
                    tree.create_node(tag=str(region), identifier=region.id, parent=parent, data=region)
                except NodeIDAbsentError:
                    print(f"Node {region.id} with non-present parent {parent}.")

        return tree

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
                try:
                    tree.create_node(tag=str(region), identifier=region.id, parent=parent, data=region)
                except NodeIDAbsentError:
                    print(f"Node {region.id} with non-present parent {parent}.")

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
                try:
                    tree.create_node(tag=str(region), identifier=region.id, parent=parent, data=region)
                except NodeIDAbsentError:
                    print(f"Node {region.id} with non-present parent {parent}.")

        # construct R-tree for each node and insert into regular tree
        for node_id in tree.expand_tree():
            node = tree.get_node(node_id)
            children = tree.children(node_id)

            indices = [self.regions.index(ch.data) for ch in children]
            rtree = self._construct_rtree([ch.data for ch in children], indices=indices, embed_obj=True)
            node.data = rtree

        return tree


    # Finding utilities
    def _maybe_validate(self, lon, lat, hits, valid_point, expected_hits=None, verbose=False):
        """
        A-priori knowledge about the validity of query points can be used to maximize the querying speed.

        If it can be assumed, that the point is inside a NUTS region, final validity checks can be skipped if the correct number of regions is present in `hits`.
        If validity can not be assumed, a final point-in-polygon test is necessary.
        """
        # TODO: only do polygon test for level3/(for non-unique levels @valid_point)?
        expected_hits = expected_hits or self.max_level-self.min_level+1
        if verbose: print("_maybe_validate:", hits)

        if valid_point and len(hits) > expected_hits:
            # TODO: smarter
            return self._find_poly(lon, lat, hits)
        elif not valid_point:
            return self._find_poly(lon, lat, hits)
        else:
            return hits

    def _get_parents(self, tree, id):
        parents = []
        current_id = id
        while parent_region := tree.parent(current_id).data:
            parents.append(parent_region)
            current_id = parent_region.id
        return parents


    def _get_full_NUTS_set(self, hits):
        """Assumption: each point either has 4 regions, or 0."""

        level3s = [hit for hit in hits if hit.level == self.max_level]
        for region in level3s:
            parents = self._get_parents(self.tree, region.id)
            if all([p in hits for p in parents]):
                return [*parents, region]
        return []


    def _get_full_NUTS_set_old(self, hits, expected_hits=None):
        """Assumption: each point either has 4 regions, or 0."""
        expected_hits = expected_hits or self.max_level-self.min_level+1

        level3s = [hit for hit in hits if hit.level == self.max_level]
        full_set = []
        for region in level3s:
            parents = self._get_parents(self.tree, region.id)
            if all([p in hits for p in parents]):
                full_set.extend(parents)
                full_set.append(region)

        full_set = np.unique(full_set).tolist()
        return full_set


    # Finding algorithms
    def _find_poly(self, lon, lat, regions, **kwargs):
        # TODO: parallel
        """Naive sequential implementation, testing every region."""
        hits = []
        p = Point((lon, lat))
        for region in regions:
            if region.geom.contains(p):
                hits.append(region)
        return hits


    def _find_bbox(self, lon, lat, regions, valid_point=False):
        """Bbox test."""
        hits = []
        for region in regions:
            xmin, ymin, xmax, ymax = region.bbox
            if (xmin <= lon <= xmax) and (ymin <= lat <= ymax):
                hits.append(region)
        hits = self._get_full_NUTS_set(hits)
        hits = self._maybe_validate(lon, lat, hits, valid_point)

        return hits


    def _candidates_rtree(self, lon, lat, regions):
        hits = [regions[i] for i in self.rtree.intersection((lon, lat, lon, lat))]
        return hits


    def _find_rtree(self, lon, lat, *args, valid_point=False):
        """Find point fast using a R-tree."""
        hits = self._candidates_rtree(lon, lat, self.regions)
        hits = self._get_full_NUTS_set(hits)
        hits = self._maybe_validate(lon, lat, hits, valid_point)

        return hits

    def _find_rtree_obj(self, lon, lat, *args, valid_point=False):
        """Find point using a R-tree. Slower variant of `_find_rtree`, due to direct embedding of objects."""
        eps = 0
        hits = list(self.rtree_obj.intersection((lon-eps, lat-eps, lon+eps, lat+eps), objects="raw"))
        hits = self._maybe_validate(lon, lat, hits, valid_point)

        return hits


    def _find_tree(self, lon, lat, *args, valid_point=False):
        """Find point fast using a Tree-Bbox-hybrid method."""
        eps = 0
        out = []
        current_node = "root"
        while children := self.tree.children(current_node):

            hits = self._find_bbox(lon, lat, [ch.data for ch in children])
            hits = self._maybe_validate(lon, lat, hits, valid_point, expected_hits=1)

            out.extend(hits)
            if hits:
                current_node = hits[0].id
            else:
                # if valid_point: raise ValueError(f"Could not locate point ({lon}, {lat}) despite `valid_point`=True.")
                break
        return out

    def _find_tree_rtree(self, lon, lat, *args, valid_point=False):
        """Find point fast using a Tree-Rtree-hybrid method."""
        eps = 0
        out = []
        current_node = "root"
        while children := self.tree_rtree.children(current_node):

            rtree = self.tree_rtree[current_node].data
            hits = [self.regions[i] for i in rtree.intersection((lon-eps, lat-eps, lon+eps, lat+eps))]
            hits = self._maybe_validate(lon, lat, hits, valid_point, expected_hits=1)

            out.extend(hits)
            if hits:
                current_node = hits[0].id
            else:
                # if valid_point: raise ValueError(f"Could not locate point ({lon}, {lat}) despite `valid_point`=True.")
                break
        return out

    def _find_tree_rtree_obj(self, lon, lat, *args, valid_point=False):
        """Find point using a Tree-Rtree-hybrid method. Slower variant of `_find_tree_rtree`, due to direct embedding of objects."""
        eps = 0
        out = []
        current_node = "root"
        while self.tree_rtree_obj.children(current_node):
            hits = list(self.tree_rtree_obj[current_node].data.intersection((lon-eps, lat-eps, lon+eps, lat+eps), objects="raw"))
            hits = self._maybe_validate(lon, lat, hits, valid_point, expected_hits=1)

            out.extend(hits)
            if hits:
                current_node = hits[0].id
            else:
                # if valid_point: raise ValueError(f"Could not locate point ({lon}, {lat}) despite `valid_point`=True.")
                break
        return out

    @property
    def __geo_interface__(self): pass       # TODO: https://gist.github.com/sgillies/2217756