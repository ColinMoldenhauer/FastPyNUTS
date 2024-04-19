import time
import re

import geojson

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

        self.year, self.scale, self.crs = self._parse_filename(geojsonfile)
        self.years = [self.year]
        self.regions = self._load_regions(level, min_level, max_level)                 # store initial regions for dynamic filtering (avoid reloading large input files for new filters)

        self.rtree = self._construct_r_tree()
        self.tree = self._construct_tree()

    def __getitem__(self, idx): return self.regions[idx]

    def __len__(self): return len(self.regions)


    # Utilities
    def _parse_filename(self, file):
        scale1, scale2, year, crs = re.search("NUTS_RG_([1-9]\d)|0(\d)M_(\d+)_(\d+)", file).groups()
        scale = scale1 or scale2
        return scale, year, crs

    def _set_level(self, level=None, min_level=0, max_level=3):
        if level:
            self.min_level = level
            self.max_level = level
        else:
            self.min_level = min_level
            self.max_level = max_level

    def _filter_regions(self, regions):
        filtered = []
        for shape in regions["features"]:
            if self.min_level <= shape["properties"]["LEVL_CODE"] <= self.max_level:
                filtered.append(shape)

        regions = [NUTSregion(feature) for feature in filtered]
        return regions

    def _load_regions(self, level=None, min_level=0, max_level=3):
        with open(self.file, encoding='cp850') as f:
            regions_in = geojson.load(f)

        self._set_level(level, min_level, max_level)
        regions_filtered = self._filter_regions(regions_in)

        return regions_filtered


    # constructing trees
    def _construct_r_tree(self):
        idx = index.Index()
        for i, region in enumerate(self.regions):
            idx.insert(id=i, coordinates=region.bbox, obj=region)
        return idx


    def _construct_tree(self):
        regions = sorted(self.regions)

        # initially construct tree
        tree = Tree()
        tree.create_node(tag="NUTS", identifier="root")
        for i, region in enumerate(sorted(regions)):
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

            rtree = index.Index()
            for i, child in enumerate(children):
                region = child.data
                rtree.insert(id=i, coordinates=region.bbox, obj=region)

            node.data = rtree

        return tree


    # Finding
    def _find_poly(self, lon, lat, regions):
        """Naive sequential implementation, testing every region."""
        hits = []
        for region in regions:
            if region.geom.intersects(Point((lon, lat))):
                hits.append(region)
        return hits

    def _find_bbox(self, lon, lat, regions):
        """Bbox test."""
        hits = []
        for region in regions:
            xmin, ymin, xmax, ymax = region.bbox
            p1 = (xmin, ymin)
            p2 = (xmin, ymax)
            p3 = (xmax, ymax)
            p4 = (xmax, ymin)
            rect = Polygon([p1, p2, p3, p4, p1])

            if rect.intersects(Point((lon, lat))):
                hits.append(region)
        return hits

    def _find_rtree(self, lon, lat, *args):
        """Find point fast using a R-tree."""
        eps = 0
        hits = list(self.rtree.intersection((lon-eps, lat-eps, lon+eps, lat+eps), objects="raw"))

        if len(hits) > self.max_level+1:
            hits = self._find_poly(lon, lat, hits)

            if len(hits) > self.max_level-self.min_level+1:
                print("more hits than expected -> investigate")
                print(f"\tmax level {self.max_level}")
                print("\tlen hits", len(hits))
                print("\tlen hits poly", len(hits))
                import pdb
                pdb.set_trace()

        return hits

    def _find_tree(self, lon, lat, *args):
        eps = 0
        out = []
        current_node = "root"
        while self.tree.children(current_node):
            hits = list(self.tree[current_node].data.intersection((lon-eps, lat-eps, lon+eps, lat+eps), objects="raw"))
            if len(hits) > 1:
                hits = self._find_poly(lon, lat, hits)

            out.extend(hits)
            if hits:
                current_node = hits[0].id
            else:
                break
        return out


    def find(self, lon, lat, method="rtree", verbose=False):
        find_ = getattr(self, f"_find_{method}")
        t0 = time.time()
        results = find_(lon, lat, self.regions)
        t1 = time.time()
        if verbose: print(f"find_{method} took {t1-t0} s")
        return sorted(results)

    @property
    def __geo_interface__(self): pass       # TODO: https://gist.github.com/sgillies/2217756