"""Free functions over :class:`FxpSpec` for the common binary-point layout."""

from __future__ import annotations

from decimal import Decimal
from typing import SupportsIndex

from ._numbers import Bytes, Number
from ._quantize import LV_ROUND_HALF_EVEN
from ._spec import FxpSpec


def to_fxp(
    value: Number,
    word_length: SupportsIndex,
    integer_word_length: SupportsIndex,
    signed: bool = True,
    *,
    clamp: bool = False,
    overflow: str = "raise",
    rounding: str = LV_ROUND_HALF_EVEN,
) -> int:
    """Encode ``value`` into an unsigned ``word_length``-bit fixed-point word.

    Keyword options (``clamp``, ``overflow``, ``rounding``) are those of
    :meth:`FxpSpec.encode`.

    >>> to_fxp("15.875", 8, 5), to_fxp(-2.5, 4, 3), to_fxp(16, 8, 5, clamp=True)
    (127, 11, 127)
    """
    return FxpSpec(word_length, integer_word_length, signed).encode(
        value, clamp=clamp, overflow=overflow, rounding=rounding
    )


def from_fxp(
    word: int, word_length: SupportsIndex, integer_word_length: SupportsIndex, signed: bool = True
) -> Decimal:
    """Decode a fixed-point ``word`` back into its exact real value.

    >>> from_fxp(0x7F, 8, 5), from_fxp(0b1011, 4, 3)
    (Decimal('15.875'), Decimal('-2.5'))
    """
    return FxpSpec(word_length, integer_word_length, signed).decode(word)


def pack_fxp(
    value: Number,
    word_length: SupportsIndex,
    integer_word_length: SupportsIndex,
    signed: bool = True,
    *,
    clamp: bool = False,
    overflow: str = "raise",
    rounding: str = LV_ROUND_HALF_EVEN,
) -> bytes:
    """Encode ``value`` and flatten it as LabVIEW does: 8 big-endian bytes, sign extended.

    >>> pack_fxp("-16", 8, 5).hex()
    'ffffffffffffff80'
    """
    return FxpSpec(word_length, integer_word_length, signed).pack(
        value, clamp=clamp, overflow=overflow, rounding=rounding
    )


def unpack_fxp(
    data: Bytes, word_length: SupportsIndex, integer_word_length: SupportsIndex, signed: bool = True
) -> Decimal:
    """Decode LabVIEW's 8-byte flattened fixed-point value into its exact real value.

    >>> unpack_fxp(bytes.fromhex("ffffffffffffffe5"), 6, 6)
    Decimal('-27')
    """
    return FxpSpec(word_length, integer_word_length, signed).unpack(data)


def pack_fxp_compact(
    value: Number,
    word_length: SupportsIndex,
    integer_word_length: SupportsIndex,
    signed: bool = True,
    *,
    clamp: bool = False,
    overflow: str = "raise",
    rounding: str = LV_ROUND_HALF_EVEN,
) -> bytes:
    """Encode ``value`` into ``ceil(word_length / 8)`` bytes: compact, not a LabVIEW form.

    >>> pack_fxp_compact(-1, 16, 16).hex()
    'ffff'
    """
    return FxpSpec(word_length, integer_word_length, signed).pack_compact(
        value, clamp=clamp, overflow=overflow, rounding=rounding
    )


def unpack_fxp_compact(
    data: Bytes, word_length: SupportsIndex, integer_word_length: SupportsIndex, signed: bool = True
) -> Decimal:
    """Decode the compact ``ceil(word_length / 8)``-byte form written by ``pack_fxp_compact``.

    >>> unpack_fxp_compact(bytes.fromhex("ffff"), 16, 16)
    Decimal('-1')
    """
    return FxpSpec(word_length, integer_word_length, signed).unpack_compact(data)
