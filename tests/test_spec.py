from decimal import Decimal

import pytest

from lvfxp import FxpError, FxpSpec


def test_resolution_is_the_least_significant_bit() -> None:
    assert FxpSpec(8, 5).resolution == Decimal("0.125")


def test_bounds_for_a_signed_layout() -> None:
    spec = FxpSpec(8, 5)
    assert spec.min_value == Decimal("-16")
    assert spec.max_value == Decimal("15.875")


def test_bounds_for_an_unsigned_layout() -> None:
    spec = FxpSpec(8, 5, signed=False)
    assert spec.min_value == Decimal("0")
    assert spec.max_value == Decimal("31.875")


def test_delta_and_offset_define_a_general_fixed_point() -> None:
    spec = FxpSpec(8, 8, signed=False, delta=Decimal("0.1"), offset=Decimal("1"))
    assert spec.encode(Decimal("1.5")) == 5
    assert spec.decode(5) == Decimal("1.5")


def test_word_length_must_be_positive() -> None:
    with pytest.raises(FxpError):
        FxpSpec(0, 0)


def test_delta_must_be_positive() -> None:
    with pytest.raises(FxpError):
        FxpSpec(8, 8, delta=Decimal("0"))


def test_float_offset_does_not_leak_binary_noise() -> None:
    spec = FxpSpec(8, 8, signed=False, delta=Decimal("1"), offset=0.1)
    assert spec.offset == Decimal("0.1")
