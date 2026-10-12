"""Exact rounding of a rational code, and LabVIEW's overflow modes."""

from __future__ import annotations

from decimal import (
    ROUND_05UP,
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
)
from fractions import Fraction

from ._errors import FxpError, FxpOverflowError

LV_TRUNCATE = ROUND_FLOOR
"""LabVIEW Truncate: drop the extra low bits, which in two's complement rounds down."""

LV_ROUND_HALF_UP = "LV_ROUND_HALF_UP"
"""LabVIEW Round-Half-Up (asymmetric): ties go toward positive infinity."""

LV_ROUND_HALF_EVEN = ROUND_HALF_EVEN
"""LabVIEW Round-Half-Even, the default rounding mode of the fixed-point type."""

ROUNDING_MODES = frozenset(
    {
        LV_ROUND_HALF_UP,
        ROUND_05UP,
        ROUND_CEILING,
        ROUND_DOWN,
        ROUND_FLOOR,
        ROUND_HALF_DOWN,
        ROUND_HALF_EVEN,
        ROUND_HALF_UP,
        ROUND_UP,
    }
)

OVERFLOW_MODES = ("raise", "saturate", "wrap")

_HALF = Fraction(1, 2)


def check_rounding(rounding: str) -> None:
    if not isinstance(rounding, str) or rounding not in ROUNDING_MODES:
        raise FxpError(f"unknown rounding mode {rounding!r}")


def overflow_mode(clamp: bool, overflow: str) -> str:
    """Resolve the legacy ``clamp`` flag and the ``overflow`` name into one mode."""
    if not isinstance(clamp, bool):
        raise FxpError("clamp must be a bool")
    if not isinstance(overflow, str) or overflow not in OVERFLOW_MODES:
        raise FxpError(f"overflow must be one of {', '.join(OVERFLOW_MODES)}, not {overflow!r}")
    if clamp:
        if overflow == "wrap":
            raise FxpError("clamp=True saturates; it cannot be combined with overflow='wrap'")
        return "saturate"
    return overflow


def round_exact(quotient: Fraction, rounding: str) -> int:
    """Round an exact rational to an integer with a ``decimal`` or LabVIEW mode."""
    check_rounding(rounding)
    floor = quotient.numerator // quotient.denominator
    rest = quotient - floor
    if rest == 0:
        return floor
    ceil = floor + 1
    toward_zero, away = (floor, ceil) if quotient > 0 else (ceil, floor)
    if rounding == ROUND_FLOOR:
        return floor
    if rounding == ROUND_CEILING:
        return ceil
    if rounding == ROUND_DOWN:
        return toward_zero
    if rounding == ROUND_UP:
        return away
    if rounding == ROUND_05UP:
        return away if abs(toward_zero) % 5 == 0 else toward_zero
    if rest != _HALF:
        return floor if rest < _HALF else ceil
    if rounding == LV_ROUND_HALF_UP:
        return ceil
    if rounding == ROUND_HALF_UP:
        return away
    if rounding == ROUND_HALF_DOWN:
        return toward_zero
    return floor if floor % 2 == 0 else ceil


def fit(coded: int, word_length: int, signed: bool, mode: str) -> int:
    """Bring a signed ``coded`` integer into the word's range using ``mode``."""
    low = -(1 << (word_length - 1)) if signed else 0
    high = (1 << (word_length - 1)) - 1 if signed else (1 << word_length) - 1
    if low <= coded <= high:
        return coded
    if mode == "saturate":
        return min(max(coded, low), high)
    if mode == "wrap":
        word = coded & ((1 << word_length) - 1)
        return word - (1 << word_length) if signed and word > high else word
    raise FxpOverflowError(f"value needs code {coded}, outside [{low}, {high}]")
