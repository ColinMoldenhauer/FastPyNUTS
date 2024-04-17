import geojson
import re


class MyNutsFinder:
    def __init__(self, geojsonfile, level=None, min_level=0, max_level=3):
        self.file = geojsonfile

        self.year, self.scale, self.crs = self._parse_filename(geojsonfile)
        self.years = [self.year]
        self.shapes_in = self._get_shapes()                 # store initial shapes for dynamic filtering (avoid reloading large input files for new filters)
        self.set_shapes(level, min_level, max_level)        # sets filtered shapes attributes

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

    def set_shapes(self, level=None, min_level=0, max_level=3):
        self._set_level(level, min_level, max_level)
        self.shapes = self._filter_shapes(self.shapes_in)

    def _filter_shapes(self, shapes):
        filtered = []
        for shape in shapes["features"]:
            if self.min_level <= shape["properties"]["LEVL_CODE"] <= self.max_level:
                filtered.append(shape)

        shapes = geojson.FeatureCollection(filtered, crs=shapes["crs"])
        return shapes

    def _get_shapes(self):
        with open(self.file) as f:
            shapes = geojson.load(f)
        return shapes

    def find(self): pass
