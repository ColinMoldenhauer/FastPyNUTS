# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


import os, sys
sys.path.insert(0, os.path.abspath('../..'))

prefixes = {
    "png": "https://raw.githubusercontent.com/ColinMoldenhauer/FastPyNUTS/develop/",
    "gif": "https://raw.githubusercontent.com/ColinMoldenhauer/FastPyNUTS/develop/",
    "ipynb": "https://github.com/ColinMoldenhauer/FastPyNUTS/tree/develop"
}

import re
import nbformat
from nbconvert import HTMLExporter


def adapt_readme(skip={0}, link_prefixes=prefixes):
    """
    Copy and adapt `README.md` in the root directory such that relative paths (images, files, etc.) are found.
    """
    with open("../../README.md", "r") as f_in:
        lines = f_in.readlines()

    with open("README.md", "w") as f_out:
        for i, line in enumerate(lines):
            if i in skip: continue
            # HTML link case: <img src="img/benchmark_1.png" alt="Benchmark for scale 1.">
            if search := re.search('<img src="(.+?)".+>', line):
                fileending = search.group(1).split(".")[-1]
                link_prefix = link_prefixes[fileending]
                line_out= re.sub('<img(.+)src="(.+?)"(.+)>', f'<img\\1src="{link_prefix}/\\2"\\3>', line)
            # Markdown link case: [](img/benchmark_other.png)
            elif (search := re.search('\[.*\]\((.+)\)', line)) and "http" not in line:
                fileending = search.group(1).split(".")[-1]
                link_prefix = link_prefixes[fileending]
                line_out = re.sub('\[(.*)\]\((.+)\)', f'[\\1]({link_prefix}/\\2)', line)
            else:
                line_out = line
            f_out.write(line_out)

def convert_notebook(nb_in, nb_out):
    with open(nb_in) as f_in:
        nb = nbformat.read(f_in, nbformat.NO_CONVERT)

    html_exporter = HTMLExporter(template_name="classic")
    (body, resources) = html_exporter.from_notebook_node(nb)

    # Write the HTML output to a file
    with open(nb_out, 'w', encoding='utf-8') as output_file:
        output_file.write(body)

adapt_readme()
convert_notebook("../../benchmark.ipynb", "_static/benchmark.html")

myst_enable_extensions = [
    "amsmath",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

project = 'fastpynuts'
copyright = '2024, Colin Moldenhauer, meengel'
author = 'Colin Moldenhauer, meengel'
release = 'latest'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    "myst_parser",
    "autodoc2",
    "sphinx.ext.autodoc", "sphinx_autodoc_typehints",
    "nbsphinx"
]

autodoc2_packages = [
    "../../fastpynuts",
]
autodoc2_render_plugin = "myst"

# autodoc2_docstring_parser_regexes = [
#     # this will render all docstrings as Markdown
#     (r".*", "myst"),
# ]

autodoc2_hidden_objects = [
    "dunder",
    "private"
]

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
html_theme_options = {
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    # Toc options
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}