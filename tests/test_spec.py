from decimal import Decimal

import pytest

from lvfxp import MAX_WORD_LENGTH, FxpError, FxpSpec


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


@pytest.mark.parametrize("word_length", [0, -1, MAX_WORD_LENGTH + 1])
def test_word_length_must_fit_labview_limits(word_length: int) -> None:
    with pytest.raises(FxpError):
        FxpSpec(word_length, 0)


def test_the_widest_labview_word_is_accepted() -> None:
    assert FxpSpec(64, 64).max_value == Decimal(2**63 - 1)
    assert FxpSpec(64, 64, signed=False).max_value == Decimal(2**64 - 1)


def test_delta_must_be_positive() -> None:
    with pytest.raises(FxpError):
        FxpSpec(8, 8, delta=Decimal("0"))


def test_float_offset_does_not_leak_binary_noise() -> None:
    spec = FxpSpec(8, 8, signed=False, delta=Decimal("1"), offset=0.1)
    assert spec.offset == Decimal("0.1")


@pytest.mark.parametrize("bad", ["abc", "nan", "inf", float("nan"), True, None, [1]])
def test_bad_values_raise_fxp_error_not_decimal_errors(bad: object) -> None:
    with pytest.raises(FxpError):
        FxpSpec(8, 5).encode(bad)  # type: ignore[arg-type]


def test_layout_fields_are_type_checked() -> None:
    with pytest.raises(FxpError):
        FxpSpec(8.0, 5)  # type: ignore[arg-type]
    with pytest.raises(FxpError):
        FxpSpec(8, True)
    with pytest.raises(FxpError):
        FxpSpec(8, 5, signed=1)  # type: ignore[arg-type]
    with pytest.raises(FxpError):
        FxpSpec(8, 5, offset="x")


def test_decode_rejects_non_integer_words() -> None:
    with pytest.raises(FxpError):
        FxpSpec(8, 5).decode(1.0)  # type: ignore[arg-type]
    with pytest.raises(FxpError):
        FxpSpec(8, 5, signed=False).decode(-1)
