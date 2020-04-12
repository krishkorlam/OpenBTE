# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

#import jupyter_sphinx


project = 'OpenBTE'
copyright = '2020, Giuseppe Romano'
author = 'Giuseppe Romano'


# The full version, including alpha/beta/rc tags
release = ''#jupyter_sphinx.__version__
# The short X.Y version
version = ''#release[: len(release) - len(release.lstrip("0123456789."))].rstrip(".")

master_doc = "index"

nbsphinx_execute = 'always'

extensions = ["sphinx.ext.mathjax","nbsphinx"]

html_theme = 'sphinx_rtd_theme'

html_theme_options = {
    'logo_only': True,
}


exclude_patterns = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

html_static_path = ['_static']