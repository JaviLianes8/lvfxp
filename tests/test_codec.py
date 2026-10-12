from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from fractions import Fraction

import pytest

from lvfxp import (
    LV_ROUND_HALF_EVEN,
    LV_ROUND_HALF_UP,
    LV_TRUNCATE,
    FxpError,
    FxpOverflowError,
    from_fxp,
    to_fxp,
)


def test_unsigned_binary_point_example() -> None:
    # 3.5 as 11.1 in binary: word length 3, integer word length 2, resolution 0.5.
    assert to_fxp(3.5, 3, 2, signed=False) == 0b111
    assert from_fxp(0b111, 3, 2, signed=False) == Decimal("3.5")


def test_signed_full_range_bounds() -> None:
    # Signed <WL=8, IWL=5>: resolution 0.125, range [-16, 15.875].
    assert to_fxp(Decimal("15.875"), 8, 5) == 0x7F
    assert to_fxp(Decimal("-16"), 8, 5) == 0x80
    assert from_fxp(0x7F, 8, 5) == Decimal("15.875")
    assert from_fxp(0x80, 8, 5) == Decimal("-16")


def test_negative_value_round_trips() -> None:
    word = to_fxp(Decimal("-2.5"), 4, 3)
    assert word == 0b1011
    assert from_fxp(word, 4, 3) == Decimal("-2.5")


def test_negative_word_is_accepted_for_signed_layout() -> None:
    assert from_fxp(-5, 4, 3) == Decimal("-2.5")


def test_integer_word_length_above_word_length() -> None:
    # <WL=4, IWL=6> signed: resolution 4, only coarse integers fit.
    assert to_fxp(12, 4, 6) == 0b0011
    assert from_fxp(0b0011, 4, 6) == Decimal("12")


def test_negative_integer_word_length_gives_fine_resolution() -> None:
    assert from_fxp(6, 4, -2, signed=False) == Decimal("0.09375")


def test_overflow_raises_by_default() -> None:
    with pytest.raises(FxpOverflowError):
        to_fxp(Decimal("16"), 8, 5)


def test_overflow_saturates_when_requested() -> None:
    assert to_fxp(Decimal("16"), 8, 5, clamp=True) == 0x7F
    assert to_fxp(Decimal("-100"), 8, 5, overflow="saturate") == 0x80


def test_overflow_wraps_like_labview() -> None:
    # Code 128 does not fit a signed byte; Wrap keeps the low 8 bits: 0x80 = -16.
    assert to_fxp(Decimal("16"), 8, 5, overflow="wrap") == 0x80
    assert to_fxp(Decimal("32"), 8, 5, signed=False, overflow="wrap") == 0
    assert to_fxp(Decimal("-0.5"), 4, 2, signed=False, overflow="wrap") == 0b1110


def test_wrap_and_clamp_cannot_be_combined() -> None:
    with pytest.raises(FxpError):
        to_fxp(1, 8, 5, clamp=True, overflow="wrap")
    with pytest.raises(FxpError):
        to_fxp(1, 8, 5, overflow="ignore")


def test_half_even_rounding_is_the_default() -> None:
    # resolution 0.125: 0.0625 -> 0.5 code (down to 0), 0.1875 -> 1.5 code (up to 2).
    assert to_fxp(Decimal("0.0625"), 8, 5) == 0
    assert to_fxp(Decimal("0.1875"), 8, 5) == 2
    assert to_fxp(Decimal("0.0625"), 8, 5, rounding=LV_ROUND_HALF_EVEN) == 0


def test_labview_half_up_sends_negative_ties_toward_positive_infinity() -> None:
    # Code -0.5: LabVIEW's asymmetric half-up gives 0, Python's ROUND_HALF_UP gives -1.
    assert to_fxp(Decimal("-0.0625"), 8, 5, rounding=LV_ROUND_HALF_UP) == 0
    assert to_fxp(Decimal("-0.0625"), 8, 5, rounding=ROUND_HALF_UP) == 0xFF
    assert to_fxp(Decimal("0.0625"), 8, 5, rounding=LV_ROUND_HALF_UP) == 1


def test_labview_truncate_rounds_toward_negative_infinity() -> None:
    assert LV_TRUNCATE == ROUND_FLOOR
    assert to_fxp(Decimal("0.1"), 8, 5, rounding=LV_TRUNCATE) == 0
    assert to_fxp(Decimal("-0.1"), 8, 5, rounding=LV_TRUNCATE) == 0xFF


def test_unknown_rounding_mode_is_rejected_even_for_exact_values() -> None:
    with pytest.raises(FxpError):
        to_fxp(1, 8, 5, rounding="ROUND_SIDEWAYS")


def test_rounding_is_exact_for_an_explicit_delta() -> None:
    from lvfxp import FxpSpec

    # 0.45 / 0.3 is exactly 1.5: half-even must pick 2, never drift to 1.
    spec = FxpSpec(8, 8, signed=False, delta=Decimal("0.3"))
    assert spec.encode(Decimal("0.45")) == 2
    assert spec.encode(Decimal("0.15")) == 0


def test_decode_rejects_a_word_that_is_too_wide() -> None:
    with pytest.raises(ValueError):
        from_fxp(256, 8, 5)


def test_smallest_resolution_stays_exact_beyond_float_and_context_precision() -> None:
    # <64, 0> has resolution 2 ** -64: 64 fractional digits, all of them kept.
    assert Fraction(from_fxp(1, 64, 0, signed=False)) == Fraction(1, 2**64)
    assert Fraction(from_fxp(2**63, 64, 0)) == Fraction(-1, 2)
