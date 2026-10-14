"""Lying objects: the library reads what an argument really is, and a caller's own error
propagates unchanged."""

from __future__ import annotations

from decimal import Decimal

import pytest

from lvfxp import FxpError, FxpOverflowError, FxpSpec


class _Lie(str):
    """A name that claims to equal "wrap" whatever text it holds."""

    def __eq__(self, other: object) -> bool:
        return str.__eq__("wrap", other)

    __hash__ = str.__hash__


def test_option_names_are_read_as_their_real_text() -> None:
    with pytest.raises(FxpOverflowError):
        FxpSpec(8, 5).encode(99, overflow=_Lie("raise"))
    with pytest.raises(FxpError, match="unknown rounding mode"):
        FxpSpec(8, 5).encode(1, rounding=_Lie("bogus"))


class _BufferLie(bytes):
    def __buffer__(self, flags: int) -> memoryview:
        return memoryview(b"\xff" * 8)


def test_a_bytes_subclass_is_read_as_the_bytes_it_holds() -> None:
    with pytest.raises(FxpError, match="got 1"):
        FxpSpec(8, 5).unpack(_BufferLie(b"\x01"))
    assert FxpSpec(8, 5).unpack(_BufferLie(bytes.fromhex("fffffffffffffff8"))) == Decimal(-1)


class _ByteArray(bytearray):
    pass


def test_a_bytearray_subclass_is_read_as_the_bytes_it_holds() -> None:
    assert FxpSpec(8, 5).unpack(_ByteArray(bytes.fromhex("fffffffffffffff8"))) == Decimal(-1)


class _FailingIndex:
    def __index__(self) -> int:
        raise TypeError("the caller's own failure")


class _FailingIter:
    def __iter__(self) -> _FailingIter:
        raise TypeError("the caller's own failure")


def test_a_callers_own_type_error_propagates_unchanged() -> None:
    with pytest.raises(TypeError, match="the caller's own failure"):
        FxpSpec(_FailingIndex(), 0)
    with pytest.raises(TypeError, match="the caller's own failure"):
        FxpSpec(8, 5).decode_many(_FailingIter())  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [8.0, Decimal(8), "8", True, None, object()])
def test_things_without_an_index_are_refused(value: object) -> None:
    with pytest.raises(FxpError, match="word_length must be an int"):
        FxpSpec(value, 0)  # type: ignore[arg-type]
