"""Free functions over :class:`FxpSpec` for the common binary-point layout."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

from ._spec import FxpSpec, Number


def to_fxp(
    value: Number,
    word_length: int,
    integer_word_length: int,
    signed: bool = True,
    *,
    clamp: bool = False,
    rounding: str = ROUND_HALF_EVEN,
) -> int:
    """Encode ``value`` into an unsigned ``word_length``-bit fixed-point word."""
    spec = FxpSpec(word_length, integer_word_length, signed)
    return spec.encode(value, clamp=clamp, rounding=rounding)


def from_fxp(
    word: int,
    word_length: int,
    integer_word_length: int,
    signed: bool = True,
) -> Decimal:
    """Decode a fixed-point ``word`` back into its exact real value."""
    spec = FxpSpec(word_length, integer_word_length, signed)
    return spec.decode(word)
