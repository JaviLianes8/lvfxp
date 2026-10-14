"""Byte forms of a fixed-point word: LabVIEW's 8-byte flatten, compact, and 1-D arrays.

LabVIEW holds every fixed-point number in a 64-bit format and sign extends it to 64 bits;
flattened numbers are big-endian. So the flattened word is 8 bytes, the word in the low
bits, sign extended when signed and zero extended when unsigned. With an overflow status
LabVIEW stores 72 bits; where that status byte sits is not documented, so it is refused.
"""

from __future__ import annotations

from collections.abc import Iterable

from ._errors import FxpError
from ._numbers import Bytes, type_name

FLATTENED_SIZE = 8
"""Bytes in a flattened LabVIEW fixed-point value (without an overflow status)."""

_COUNT_SIZE = 4
_MAX_COUNT = (1 << 31) - 1


def as_bytes(data: object) -> bytes:
    """Return the raw bytes of a bytes-like ``data`` (any memoryview format, flattened)."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise FxpError(f"expected bytes, not {type_name(data)}")
    try:
        return memoryview(data).tobytes()  # the real buffer, whatever a subclass claims
    except ValueError:
        raise FxpError("expected bytes, got a released memoryview") from None


def _coded(word: int, word_length: int, signed: bool) -> int:
    if signed and word >> (word_length - 1):
        return word - (1 << word_length)
    return word


def compact_size(word_length: int) -> int:
    return (word_length + 7) // 8


def flatten_word(word: int, word_length: int, signed: bool) -> bytes:
    """Return the 8 big-endian bytes LabVIEW flattens an unsigned ``word`` to."""
    return _coded(word, word_length, signed).to_bytes(FLATTENED_SIZE, "big", signed=signed)


def _size_error(got: int) -> FxpError:
    message = f"a flattened fixed-point value is {FLATTENED_SIZE} bytes, got {got}"
    if got == FLATTENED_SIZE + 1:
        message += (
            "; 9 bytes suggests a value with an overflow status, which lvfxp does not"
            " decode because LabVIEW does not document where the status byte sits"
        )
    return FxpError(message)


def unflatten_word(data: Bytes, word_length: int, signed: bool) -> int:
    """Return the unsigned word held in 8 flattened bytes.

    The bits above the word must be its sign extension (zeros when unsigned), as LabVIEW
    writes them; anything else means the bytes belong to another layout.
    """
    data = as_bytes(data)
    if len(data) != FLATTENED_SIZE:
        raise _size_error(len(data))
    raw = int.from_bytes(data, "big", signed=signed)
    low = -(1 << (word_length - 1)) if signed else 0
    high = (1 << (word_length - 1)) - 1 if signed else (1 << word_length) - 1
    if not low <= raw <= high:
        sign = "signed" if signed else "unsigned"
        raise FxpError(
            f"bytes {data.hex()} are not a {sign} {word_length}-bit word extended to"
            f" 64 bits; check the word length and signedness"
        )
    return raw & ((1 << word_length) - 1)


def compact_word(word: int, word_length: int) -> bytes:
    """Return ``word`` in ``ceil(word_length / 8)`` big-endian bytes (not a LabVIEW form)."""
    return word.to_bytes(compact_size(word_length), "big")


def uncompact_word(data: Bytes, word_length: int) -> int:
    """Read a compact word, ignoring any bits above ``word_length``."""
    data = as_bytes(data)
    size = compact_size(word_length)
    if len(data) != size:
        raise FxpError(f"expected {size} compact bytes, got {len(data)}")
    return int.from_bytes(data, "big") & ((1 << word_length) - 1)


def flatten_array(words: Iterable[int], word_length: int, signed: bool) -> bytes:
    """Flatten a 1-D array: a big-endian 32-bit count, then each 8-byte element."""
    items = [flatten_word(word, word_length, signed) for word in words]
    if len(items) > _MAX_COUNT:
        raise FxpError(f"a flattened array holds at most {_MAX_COUNT} elements")
    return len(items).to_bytes(_COUNT_SIZE, "big") + b"".join(items)


def unflatten_array(data: Bytes, word_length: int, signed: bool) -> list[int]:
    """Read a flattened 1-D array back into unsigned words; the length must match exactly."""
    data = as_bytes(data)
    if len(data) < _COUNT_SIZE:
        raise FxpError(f"a flattened array starts with a {_COUNT_SIZE}-byte count")
    count = int.from_bytes(data[:_COUNT_SIZE], "big", signed=True)
    body = data[_COUNT_SIZE:]
    if count < 0 or len(body) != count * FLATTENED_SIZE:
        raise FxpError(
            f"array count {count} needs {max(count, 0) * FLATTENED_SIZE} element bytes,"
            f" got {len(body)}"
        )
    return [
        unflatten_word(body[start : start + FLATTENED_SIZE], word_length, signed)
        for start in range(0, len(body), FLATTENED_SIZE)
    ]
