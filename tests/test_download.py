import os
import pytest

from fastpynuts import NUTSfinder
from fastpynuts.download import _download_NUTS


@pytest.mark.parametrize("input", [
    {},
    {"year": 2006},
    {"scale": 20},
    {"epsg": 3035},
])
class TestDownload:
    def test_file(self, tmp_path, input):
        file = _download_NUTS(tmp_path, **input)
        assert os.path.exists(file)

    def test_nf(self, tmp_path, input):
        nf = NUTSfinder.from_web(**input)