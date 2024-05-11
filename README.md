# FastPyNUTS
A fast implementation of querying the [NUTS - Nomenclature of territorial units for statistics](https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units-statistical-units/nuts) dataset by location, particularly useful for large-scale applications.


![Figure: NUTS levels (Eurostat)](img/levels.gif) <br>
<!-- ![Figure: NUTS levels (Eurostat)](https://github.com/ColinMoldenhauer/FastPyNUTS/blob/main/levels.gif) <br> -->
_Figure: Eurostat_
<!-- _Figure: [Eurostat](https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units-statistical-units/nuts)_ -->


## Usage


```python
from fastpynuts import NUTSfinder

# construct from local file
nf = NUTSfinder("PATH_TO_LOCAL_FILE.geojson")

# retrieve data automatically (file will be downloaded to or if already existing read from '.data')
nf = NUTSfinder.from_web(scale=1, year=2021, epsg=4326)


# find NUTS regions
point = (11.57, 48.13)
regions = nf.find(*point)                   # find all regions
some_regions = nf.find_level(*point, 3)     # only find NUTS-3 regions
```

## Features
- fast querying of NUTS regions using an R-tree
- query user-defined NUTS-levels (0-3)
- use your own custom NUTS dataset (other CRS, ...)


## Installation
```cmd
pip install fastpynuts
```
`FastPyNUTS` requires `geojson`, `numpy`, `shapely`, `treelib` and `rtree`



## Advanced Usage
```python
# apply a buffer to the input regions to catch points on the boundary (for further info on the buffering, see the documentation)
nf = NUTSfinder("PATH_TO_LOCAL_FILE.geojson", buffer_geoms=1e-5)

# only load certain levels of regions (here levels 2 and 3)
nf = NUTSfinder("PATH_TO_LOCAL_FILE.geojson", min_level=2, max_level=3)


# if the point to be queried is guaranteed to lie within a NUTS region, setting valid_point to True may speed up the runtime
regions = nf.find(*point, valid_point=True)
```


## Runtime Comparison
![benchmark](img/benchmark.png)
For a full runtime analysis, see [benchmark.ipynb](benchmark.ipynb)



## Contributors
- [Colin Moldenhauer](https://github.com/ColinMoldenhauer/)
- [meengel](https://github.com/meengel)
