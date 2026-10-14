"""Contracts for mutations the second independent review round found the suite did not catch."""

from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

import pytest

import lvfxp._numbers
from lvfxp import FxpError, FxpSpec


class _InstanceGetitem:
    """Has ``__getitem__`` only on the instance, which ``iter()`` does not use."""

    def __init__(self) -> None:
        self.__getitem__ = lambda index: 0


def test_an_instance_level_getitem_is_refused_with_fxp_error() -> None:
    with pytest.raises(FxpError, match="values must be an iterable"):
        FxpSpec(8, 5).encode_many(_InstanceGetitem())  # type: ignore[arg-type]


def _named(length: int) -> object:
    return type("N" * length, (), {})()


def test_a_type_name_of_exactly_the_limit_is_shown_whole() -> None:
    with pytest.raises(FxpError) as whole:
        FxpSpec(8, 5).encode(_named(40))  # type: ignore[arg-type]
    assert str(whole.value).endswith("N" * 40)
    with pytest.raises(FxpError) as cut:
        FxpSpec(8, 5).encode(_named(41))  # type: ignore[arg-type]
    assert str(cut.value).endswith("N" * 40 + "...")


class _Spy(Decimal):
    seen: ClassVar[list[type]] = []

    def __new__(cls, value: object = "0", context: object = None) -> _Spy:
        _Spy.seen.append(type(value))
        return Decimal.__new__(cls, value, context)  # type: ignore[arg-type]


def test_the_huge_integer_guard_sits_exactly_at_34000_bits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lvfxp._numbers, "Decimal", _Spy)
    _Spy.seen.clear()
    with pytest.raises(FxpError, match="exponent beyond"):
        lvfxp._numbers.as_decimal(1 << 33_999)  # 34000 bits: converted, then refused
    assert int in _Spy.seen
    _Spy.seen.clear()
    with pytest.raises(FxpError, match="exponent beyond"):
        lvfxp._numbers.as_decimal(1 << 34_000)  # 34001 bits: refused before converting
    assert int not in _Spy.seen
