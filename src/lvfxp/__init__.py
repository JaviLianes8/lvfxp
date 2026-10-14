"""Encode and decode LabVIEW fixed-point (FXP) numbers in pure Python.

Constants: ``FLATTENED_SIZE`` (bytes in LabVIEW's flattened form), ``MAX_WORD_LENGTH``
(LabVIEW's widest word), ``MAX_INTEGER_WORD_LENGTH`` (lvfxp's bound on the integer word
length) and the LabVIEW rounding modes ``LV_ROUND_HALF_EVEN``, ``LV_ROUND_HALF_UP`` and
``LV_TRUNCATE``.

>>> import lvfxp
>>> lvfxp.FLATTENED_SIZE, lvfxp.MAX_WORD_LENGTH, lvfxp.MAX_INTEGER_WORD_LENGTH
(8, 64, 4096)
>>> lvfxp.to_fxp("-0.0625", 8, 5, rounding=lvfxp.LV_ROUND_HALF_UP)
0
>>> lvfxp.to_fxp("0.0625", 8, 5, rounding=lvfxp.LV_ROUND_HALF_EVEN)
0
>>> lvfxp.to_fxp("-0.1", 8, 5, rounding=lvfxp.LV_TRUNCATE)
255
"""

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
from ._layout import MAX_INTEGER_WORD_LENGTH, MAX_WORD_LENGTH
from ._quantize import LV_ROUND_HALF_EVEN, LV_ROUND_HALF_UP, LV_TRUNCATE, EncodeOptions
from ._spec import FxpSpec

__version__ = "1.0.0"

__all__ = [
    "FLATTENED_SIZE",
    "LV_ROUND_HALF_EVEN",
    "LV_ROUND_HALF_UP",
    "LV_TRUNCATE",
    "MAX_INTEGER_WORD_LENGTH",
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
