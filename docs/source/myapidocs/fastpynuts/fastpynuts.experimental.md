# {py:mod}`fastpynuts.experimental`

```{py:module} fastpynuts.experimental
```

```{autodoc2-docstring} fastpynuts.experimental
:allowtitles:
```

## Module Contents

### Classes

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`NUTSfinderBenchmark <fastpynuts.experimental.NUTSfinderBenchmark>`
  - ```{autodoc2-docstring} fastpynuts.experimental.NUTSfinderBenchmark
    :summary:
    ```
````

### API

`````{py:class} NUTSfinderBenchmark(geojsonfile, buffer_geoms=0, min_level=0, max_level=3)
:canonical: fastpynuts.experimental.NUTSfinderBenchmark

Bases: {py:obj}`fastpynuts.fastpynuts.NUTSfinder`

```{autodoc2-docstring} fastpynuts.experimental.NUTSfinderBenchmark
```

```{rubric} Initialization
```

```{autodoc2-docstring} fastpynuts.experimental.NUTSfinderBenchmark.__init__
```

````{py:method} find(lon, lat, method='tree', valid_point=False, verbose=False, **kwargs)
:canonical: fastpynuts.experimental.NUTSfinderBenchmark.find

```{autodoc2-docstring} fastpynuts.experimental.NUTSfinderBenchmark.find
```

````

````{py:method} from_web(scale=1, year=2021, epsg=4326, datadir='.data', **kwargs)
:canonical: fastpynuts.experimental.NUTSfinderBenchmark.from_web
:classmethod:

````

````{py:method} find_level(lon, lat, level, valid_point=False)
:canonical: fastpynuts.experimental.NUTSfinderBenchmark.find_level

````

`````
