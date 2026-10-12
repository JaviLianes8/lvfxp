"""Every input outside lvfxp's bounds raises FxpError quickly, never another exception."""

from __future__ import annotations

import time
from decimal import Decimal
from fractions import Fraction

import pytest

from lvfxp import MAX_INTEGER_WORD_LENGTH, FxpError, FxpSpec, from_fxp, to_fxp, unpack_fxp


@pytest.mark.parametrize("iwl", [MAX_INTEGER_WORD_LENGTH + 1, -MAX_INTEGER_WORD_LENGTH - 1])
def test_integer_word_length_beyond_the_bound_is_refused(iwl: int) -> None:
    with pytest.raises(FxpError, match="integer_word_length"):
        FxpSpec(8, iwl)


@pytest.mark.parametrize("iwl", [MAX_INTEGER_WORD_LENGTH, -MAX_INTEGER_WORD_LENGTH])
def test_integer_word_length_at_the_bound_is_exact(iwl: int) -> None:
    spec = FxpSpec(64, iwl)
    assert Fraction(spec.resolution) == Fraction(2) ** (iwl - 64)
    assert from_fxp(1, 64, iwl) == spec.resolution
    assert to_fxp(spec.resolution, 64, iwl) == 1


@pytest.mark.parametrize("text", ["1e2000000", "-1e999999999", "1e-20000", "1.5e-10001"])
def test_huge_decimal_exponents_fail_fast(text: str) -> None:
    start = time.perf_counter()
    with pytest.raises(FxpError, match="exponent"):
        to_fxp(text, 8, 5, overflow="saturate")
    assert time.perf_counter() - start < 1


def test_zero_with_a_huge_exponent_is_zero() -> None:
    assert to_fxp("0e-999999", 8, 5) == 0


@pytest.mark.parametrize("name", ["delta", "offset"])
def test_layout_numbers_share_the_exponent_bound(name: str) -> None:
    with pytest.raises(FxpError, match=name):
        FxpSpec(8, 5, **{name: Decimal("1e20000")})  # type: ignore[arg-type]


def test_option_types_are_checked() -> None:
    with pytest.raises(FxpError, match="rounding"):
        to_fxp(1, 8, 5, rounding=[1])  # type: ignore[arg-type]
    with pytest.raises(FxpError, match="clamp"):
        to_fxp(100, 8, 5, clamp="no")  # type: ignore[arg-type]
    with pytest.raises(FxpError, match="overflow"):
        to_fxp(1, 8, 5, overflow=["wrap"])  # type: ignore[arg-type]


@pytest.mark.parametrize("data", [[0] * 8, "abcdabcd", 12345678])
def test_unpacking_requires_bytes(data: object) -> None:
    spec = FxpSpec(8, 5)
    for unpack in (spec.unpack, spec.unpack_compact, spec.unpack_array):
        with pytest.raises(FxpError, match="expected bytes"):
            unpack(data)  # type: ignore[arg-type]
    with pytest.raises(FxpError):
        unpack_fxp(data, 8, 5)  # type: ignore[arg-type]


def test_memoryview_is_accepted() -> None:
    assert FxpSpec(8, 5).unpack(memoryview(bytes.fromhex("ffffffffffffff80"))) == -16
