from decimal import ROUND_HALF_EVEN, Decimal

import pytest

from lvfxp import FxpOverflowError, from_fxp, to_fxp


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


def test_round_trip_over_the_whole_word() -> None:
    for word in range(1 << 6):
        value = from_fxp(word, 6, 3)
        assert to_fxp(value, 6, 3) == word


def test_overflow_raises_by_default() -> None:
    with pytest.raises(FxpOverflowError):
        to_fxp(Decimal("16"), 8, 5)


def test_overflow_clamps_when_requested() -> None:
    assert to_fxp(Decimal("16"), 8, 5, clamp=True) == 0x7F
    assert to_fxp(Decimal("-100"), 8, 5, clamp=True) == 0x80


def test_half_even_rounding_is_the_default() -> None:
    # resolution 0.125: 0.0625 -> 0.5 code (down to 0), 0.1875 -> 1.5 code (up to 2).
    assert to_fxp(Decimal("0.0625"), 8, 5) == 0
    assert to_fxp(Decimal("0.1875"), 8, 5) == 2


def test_rounding_mode_is_configurable() -> None:
    from decimal import ROUND_FLOOR

    assert to_fxp(Decimal("0.1"), 8, 5, rounding=ROUND_FLOOR) == 0
    assert to_fxp(Decimal("0.1"), 8, 5, rounding=ROUND_HALF_EVEN) == 1


def test_decode_rejects_a_word_that_is_too_wide() -> None:
    with pytest.raises(ValueError):
        from_fxp(256, 8, 5)


def test_small_fraction_stays_exact_beyond_float_precision() -> None:
    # resolution 2**-64 has 64 fractional digits; Decimal keeps every one.
    expected = Decimal(5**64).scaleb(-64)
    assert from_fxp(1, 65, 1) == expected
