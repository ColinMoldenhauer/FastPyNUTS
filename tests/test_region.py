import pytest

from .utils import get_regions

@pytest.mark.parametrize("region", get_regions())
def test_geo_interface(region):
    assert region.feature == region.__geo_interface__

@pytest.mark.parametrize("regions", [get_regions()])
def test_sorted(regions):
    assert [str(reg) for reg in sorted(regions)] == sorted([str(reg) for reg in regions])
