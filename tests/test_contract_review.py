"""Contracts for mutations that the independent review round found the suite did not catch."""

from __future__ import annotations

from decimal import Decimal

import pytest

from lvfxp import FxpError, FxpSpec, to_fxp


def test_resolution_keeps_the_spelling_of_its_own_delta() -> None:
    assert str(FxpSpec(8, 8, delta="0.1").resolution) == "0.1"
    assert str(FxpSpec(8, 8, delta="0.10").resolution) == "0.10"
    assert str(FxpSpec(8, 8, delta="0.1").resolution) == "0.1"


@pytest.mark.parametrize("delta", ["0.5", 0.5, Decimal("0.5")])
def test_delta_is_stored_as_decimal_whatever_was_passed(delta: object) -> None:
    spec = FxpSpec(8, 8, delta=delta)  # type: ignore[arg-type]
    assert type(spec.delta) is Decimal
    assert spec == FxpSpec(8, 8, delta=Decimal("0.5"))
    assert hash(spec) == hash(FxpSpec(8, 8, delta=Decimal("0.5")))


def test_decode_refuses_a_signed_code_one_below_the_minimum() -> None:
    assert FxpSpec(8, 5).decode(-128) == Decimal("-16")
    with pytest.raises(FxpError, match="out of range"):
        FxpSpec(8, 5).decode(-129)


class _ClaimsHalfEven(str):
    """A rounding name that claims to be ROUND_HALF_EVEN whatever text it holds."""

    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return hash("ROUND_HALF_EVEN")


def test_a_rounding_name_is_read_as_its_real_text() -> None:
    with pytest.raises(FxpError, match="unknown rounding mode"):
        to_fxp(1, 8, 5, rounding=_ClaimsHalfEven("bogus"))


class _OldSequence:
    """Iterable only through the old __getitem__ protocol."""

    def __getitem__(self, index: int) -> int:
        if index >= 3:
            raise IndexError(index)
        return index


def test_batches_accept_a_getitem_only_sequence() -> None:
    assert FxpSpec(8, 5).encode_many(_OldSequence()) == [0, 8, 16]  # type: ignore[arg-type]
    assert FxpSpec(8, 5).decode_many(_OldSequence()) == [  # type: ignore[arg-type]
        Decimal("0"),
        Decimal("0.125"),
        Decimal("0.250"),
    ]


class _FakeInt:
    @property  # type: ignore[misc]
    def __class__(self) -> type:
        return int


def test_an_integer_field_faking_its_class_is_refused_with_fxp_error() -> None:
    with pytest.raises(FxpError, match="word_length must be an int"):
        FxpSpec(_FakeInt(), 5)  # type: ignore[arg-type]
    with pytest.raises(FxpError, match="word must be an int"):
        FxpSpec(8, 5).decode(_FakeInt())  # type: ignore[arg-type]


class _Float(float):
    def __repr__(self) -> str:
        return f"_Float({float.__repr__(self)})"


def test_a_float_subclass_is_read_through_the_float_repr() -> None:
    assert to_fxp(_Float(1.5), 8, 5) == 12
    assert FxpSpec(8, 5, offset=_Float(0.5)).offset == Decimal("0.5")


class _BytesLie(bytearray):
    def __bytes__(self) -> bytes:
        return b"\x00" * 8


def test_a_bytearray_subclass_cannot_swap_its_bytes() -> None:
    data = _BytesLie(bytes.fromhex("fffffffffffffff8"))
    assert FxpSpec(8, 5).unpack(data) == Decimal(-1)
