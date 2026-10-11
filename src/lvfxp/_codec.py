"""Free functions over :class:`FxpSpec` for the common binary-point layout."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from ._numbers import Number
from ._spec import EncodeOptions, FxpSpec

if TYPE_CHECKING:
    from typing_extensions import Unpack


def to_fxp(
    value: Number,
    word_length: int,
    integer_word_length: int,
    signed: bool = True,
    **options: Unpack[EncodeOptions],
) -> int:
    """Encode ``value`` into an unsigned ``word_length``-bit fixed-point word.

    Keyword options (``clamp``, ``overflow``, ``rounding``) are those of
    :meth:`FxpSpec.encode`.
    """
    return FxpSpec(word_length, integer_word_length, signed).encode(value, **options)


def from_fxp(word: int, word_length: int, integer_word_length: int, signed: bool = True) -> Decimal:
    """Decode a fixed-point ``word`` back into its exact real value."""
    return FxpSpec(word_length, integer_word_length, signed).decode(word)


def pack_fxp(
    value: Number,
    word_length: int,
    integer_word_length: int,
    signed: bool = True,
    **options: Unpack[EncodeOptions],
) -> bytes:
    """Encode ``value`` and flatten it as LabVIEW does: 8 big-endian bytes, sign extended."""
    return FxpSpec(word_length, integer_word_length, signed).pack(value, **options)


def unpack_fxp(
    data: bytes | bytearray, word_length: int, integer_word_length: int, signed: bool = True
) -> Decimal:
    """Decode LabVIEW's 8-byte flattened fixed-point value into its exact real value."""
    return FxpSpec(word_length, integer_word_length, signed).unpack(data)


def pack_fxp_compact(
    value: Number,
    word_length: int,
    integer_word_length: int,
    signed: bool = True,
    **options: Unpack[EncodeOptions],
) -> bytes:
    """Encode ``value`` into ``ceil(word_length / 8)`` bytes: compact, not a LabVIEW form."""
    return FxpSpec(word_length, integer_word_length, signed).pack_compact(value, **options)


def unpack_fxp_compact(
    data: bytes | bytearray, word_length: int, integer_word_length: int, signed: bool = True
) -> Decimal:
    """Decode the compact ``ceil(word_length / 8)``-byte form written by ``pack_fxp_compact``."""
    return FxpSpec(word_length, integer_word_length, signed).unpack_compact(data)
