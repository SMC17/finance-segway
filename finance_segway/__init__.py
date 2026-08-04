"""Finance-Segway reference engines.

Pure-Python, dependency-free implementations used as independent oracles for
spreadsheet builders. These functions intentionally avoid Excel-specific
state so they can be ported to Zig and compared cross-language later.
"""

from .engines import *  # noqa: F401,F403
