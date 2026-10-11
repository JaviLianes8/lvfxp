"""Encode and decode LabVIEW fixed-point (FXP) numbers in pure Python."""

from __future__ import annotations

from ._codec import (
    from_fxp,
    pack_fxp,
    pack_fxp_compact,
    to_fxp,
    unpack_fxp,
    unpack_fxp_compact,
)
from ._errors import FxpError, FxpOverflowError
from ._flat import FLATTENED_SIZE
from ._quantize import LV_ROUND_HALF_EVEN, LV_ROUND_HALF_UP, LV_TRUNCATE
from ._spec import MAX_WORD_LENGTH, EncodeOptions, FxpSpec

__version__ = "0.3.0"

__all__ = [
    "FLATTENED_SIZE",
    "LV_ROUND_HALF_EVEN",
    "LV_ROUND_HALF_UP",
    "LV_TRUNCATE",
    "MAX_WORD_LENGTH",
    "EncodeOptions",
    "FxpError",
    "FxpOverflowError",
    "FxpSpec",
    "from_fxp",
    "pack_fxp",
    "pack_fxp_compact",
    "to_fxp",
    "unpack_fxp",
    "unpack_fxp_compact",
]
