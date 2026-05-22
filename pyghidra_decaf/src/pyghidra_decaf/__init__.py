"""
PyGhidra Plugin - Python package for Ghidra plugins.
"""

from importlib.metadata import (
    PackageNotFoundError,
    version,
)

try:
    __version__ = version('pyghidra_decaf')
except PackageNotFoundError:
    __version__ = '0.0.0+unknown'
