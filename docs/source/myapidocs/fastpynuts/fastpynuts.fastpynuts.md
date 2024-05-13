# {py:mod}`fastpynuts.fastpynuts`

```{py:module} fastpynuts.fastpynuts
```

```{autodoc2-docstring} fastpynuts.fastpynuts
:allowtitles:
```

## Module Contents

### Classes

````{list-table}
:class: autosummary longtable
:align: left

* - {py:obj}`NUTSregion <fastpynuts.fastpynuts.NUTSregion>`
  - ```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSregion
    :summary:
    ```
* - {py:obj}`NUTSfinder <fastpynuts.fastpynuts.NUTSfinder>`
  - ```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSfinder
    :summary:
    ```
````

### API

`````{py:class} NUTSregion(feature, buffer=None)
:canonical: fastpynuts.fastpynuts.NUTSregion

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSregion
```

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSregion.__init__
```

````{py:property} id -> int
:canonical: fastpynuts.fastpynuts.NUTSregion.id

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSregion.id
```

````

````{py:property} level
:canonical: fastpynuts.fastpynuts.NUTSregion.level

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSregion.level
```

````

````{py:property} type
:canonical: fastpynuts.fastpynuts.NUTSregion.type

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSregion.type
```

````


`````

`````{py:class} NUTSfinder(geojsonfile, buffer_geoms=0, min_level=0, max_level=3)
:canonical: fastpynuts.fastpynuts.NUTSfinder

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSfinder
```

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSfinder.__init__
```

````{py:method} from_web(scale=1, year=2021, epsg=4326, datadir='.data', **kwargs) -> NUTSfinder
:canonical: fastpynuts.fastpynuts.NUTSfinder.from_web
:classmethod:

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSfinder.from_web
```

````

````{py:method} find(lon, lat, valid_point=False, **kwargs) -> list
:canonical: fastpynuts.fastpynuts.NUTSfinder.find

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSfinder.find
```

````

````{py:method} find_level(lon, lat, level, valid_point=False) -> list
:canonical: fastpynuts.fastpynuts.NUTSfinder.find_level

```{autodoc2-docstring} fastpynuts.fastpynuts.NUTSfinder.find_level
```

````

`````