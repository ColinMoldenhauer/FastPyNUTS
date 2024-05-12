import time

from shapely import intersects_xy
from treelib import Tree

from .fastpynuts import NUTSfinder


class NUTSfinderBenchmark(NUTSfinder):
    """
    Implements various experimental methods to find corresponding NUTS regions for benchmark purposes.


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
    def __init__(self, geojsonfile, buffer_geoms=0, min_level=0, max_level=3):
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


    # constructing trees
    # def _create_dict_tree(ids, cumul=""):
    #     if len(ids) == 1: return {cumul + ids[0]: None}
    #     for id in ids:
    #         return {cumul + id: _create_dict_tree(ids[1:], cumul + id)}


    # for key in keys:
    #     ids = [key[:2], *key[2:]]
    #     new = create_tree(ids)
    #     print(new)
    #     d.update(new)

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
