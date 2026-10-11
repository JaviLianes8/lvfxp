"""Encode and decode LabVIEW fixed-point (FXP) numbers in pure Python."""

from __future__ import annotations

from ._codec import from_fxp, pack_fxp, to_fxp, unpack_fxp
from ._errors import FxpError, FxpOverflowError
from ._spec import FxpSpec

__version__ = "0.2.0"

__all__ = [
    "FxpError",
    "FxpOverflowError",
    "FxpSpec",
    "from_fxp",
    "pack_fxp",
    "to_fxp",
    "unpack_fxp",
]
