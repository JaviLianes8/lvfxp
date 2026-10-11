"""Encode and decode LabVIEW fixed-point (FXP) numbers in pure Python."""

from __future__ import annotations

from ._codec import from_fxp, to_fxp
from ._errors import FxpError, FxpOverflowError
from ._spec import FxpSpec

__version__ = "0.1.0"

__all__ = [
    "FxpError",
    "FxpOverflowError",
    "FxpSpec",
    "from_fxp",
    "to_fxp",
]
