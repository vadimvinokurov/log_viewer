"""Build configuration for Cython extensions."""
from __future__ import annotations

import numpy
from Cython.Build import cythonize
from setuptools import Extension, setup

extensions = [
    Extension(
        "log_viewer.core._parser_cy",
        sources=["src/log_viewer/core/_parser_cy.pyx"],
        include_dirs=[".", numpy.get_include()],
    ),
]

setup(
    ext_modules=cythonize(extensions, language_level="3"),
)