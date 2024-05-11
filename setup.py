import os, io, re
from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))

version = os.environ.get("FASTPYNUTS_VERSION", None)
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = None

setup(
    version=version,
    long_description=long_description
)