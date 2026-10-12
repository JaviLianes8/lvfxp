"""The contract: every public name keeps its documented promise, end to end.

Expected results are computed here independently, with ``fractions.Fraction`` and plain
integer arithmetic, never by calling the library twice. The sweep covers every word of
each word length up to 8 bits, signed and unsigned, at several integer word lengths.
"""

from __future__ import annotations

import importlib.resources
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

import pytest

import lvfxp
from lvfxp import (
    LV_ROUND_HALF_EVEN,
    LV_ROUND_HALF_UP,
    LV_TRUNCATE,
    FxpError,
    FxpOverflowError,
    FxpSpec,
)

PUBLIC_API: list[str] = [
    "FLATTENED_SIZE",
    "LV_ROUND_HALF_EVEN",
    "LV_ROUND_HALF_UP",
    "LV_TRUNCATE",
    "MAX_INTEGER_WORD_LENGTH",
    "MAX_WORD_LENGTH",
    "EncodeOptions",
    "FxpError",
    "FxpOverflowError",
    "FxpSpec",
    "from_fxp",
    "pack_fxp",
    "pack_fxp_compact",
    "to_fxp",
    "unpack_fxp",
    "unpack_fxp_compact",
]

LAYOUTS = [
    (wl, iwl, signed)
    for wl in range(1, 9)
    for iwl in sorted({-3, 0, wl // 2, wl, wl + 3})
    for signed in (True, False)
]


def _coded(word: int, wl: int, signed: bool) -> int:
    return word - (1 << wl) if signed and word >= 1 << (wl - 1) else word


def _value(coded: int, wl: int, iwl: int) -> Fraction:
    return coded * Fraction(2) ** (iwl - wl)


def _decimal(exact: Fraction) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 100
        result = Decimal(exact.numerator) / Decimal(exact.denominator)
    assert Fraction(result) == exact
    return result


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvfxp.__all__) == sorted(PUBLIC_API)
    assert all(hasattr(lvfxp, name) for name in lvfxp.__all__)


def test_version_and_type_information_ship() -> None:
    assert lvfxp.__version__ == "0.3.0"
    assert importlib.resources.files("lvfxp").joinpath("py.typed").is_file()


@pytest.mark.parametrize(("wl", "iwl", "signed"), LAYOUTS)
def test_every_word_keeps_value_math_and_both_byte_forms(wl: int, iwl: int, signed: bool) -> None:
    spec = FxpSpec(wl, iwl, signed)
    assert Fraction(spec.resolution) == Fraction(2) ** (iwl - wl)
    low = -(1 << (wl - 1)) if signed else 0
    high = (1 << (wl - 1)) - 1 if signed else (1 << wl) - 1
    assert Fraction(spec.min_value) == _value(low, wl, iwl)
    assert Fraction(spec.max_value) == _value(high, wl, iwl)
    for word in range(1 << wl):
        coded = _coded(word, wl, signed)
        value = spec.decode(word)
        assert Fraction(value) == _value(coded, wl, iwl)
        assert spec.encode(value) == word
        flat = (coded % (1 << 64)).to_bytes(8, "big")
        assert spec.pack(value) == flat
        assert spec.unpack(flat) == value
        assert spec.pack_compact(value) == word.to_bytes((wl + 7) // 8, "big")
        assert spec.unpack_compact(word.to_bytes((wl + 7) // 8, "big")) == value


@pytest.mark.parametrize(("wl", "iwl", "signed"), LAYOUTS)
def test_every_tie_rounds_by_its_documented_mode(wl: int, iwl: int, signed: bool) -> None:
    spec = FxpSpec(wl, iwl, signed)
    low = -(1 << (wl - 1)) if signed else 0
    for coded in range(low, low + (1 << wl) - 1):
        tie = _decimal((coded + Fraction(1, 2)) * Fraction(2) ** (iwl - wl))
        even = coded if coded % 2 == 0 else coded + 1
        away = coded + 1 if coded >= 0 else coded
        words = {
            LV_ROUND_HALF_EVEN: even,
            LV_ROUND_HALF_UP: coded + 1,
            LV_TRUNCATE: coded,
            ROUND_HALF_UP: away,
        }
        for rounding, expected in words.items():
            assert spec.encode(tie, rounding=rounding) == expected % (1 << wl)


@pytest.mark.parametrize(("wl", "iwl", "signed"), LAYOUTS)
def test_overflow_raises_saturates_or_wraps(wl: int, iwl: int, signed: bool) -> None:
    spec = FxpSpec(wl, iwl, signed)
    step = spec.resolution
    span = 1 << wl
    low = -(1 << (wl - 1)) if signed else 0
    high = low + span - 1
    for beyond, nearest in ((spec.max_value + step, high), (spec.min_value - step, low)):
        with pytest.raises(FxpOverflowError):
            spec.encode(beyond)
        assert spec.encode(beyond, overflow="saturate") == nearest % span
        assert spec.encode(beyond, clamp=True) == nearest % span
    assert spec.encode(spec.max_value + step, overflow="wrap") == low % span
    assert spec.encode(spec.min_value - step, overflow="wrap") == high % span


def test_the_widest_words_flatten_to_their_full_eight_bytes() -> None:
    assert FxpSpec(64, 0).pack(Decimal("-0.5")) == bytes.fromhex("8000000000000000")
    assert FxpSpec(64, 64, False).pack(2**64 - 1) == bytes.fromhex("ffffffffffffffff")
    assert FxpSpec(1, 1).pack(-1) == bytes.fromhex("ffffffffffffffff")
    assert FxpSpec(1, 1, False).pack(1) == bytes.fromhex("0000000000000001")


def test_free_functions_agree_with_the_spec() -> None:
    assert lvfxp.to_fxp(Decimal("-2.5"), 4, 3) == FxpSpec(4, 3).encode(Decimal("-2.5"))
    assert lvfxp.from_fxp(0xB, 4, 3) == Decimal("-2.5")
    assert lvfxp.pack_fxp(Decimal("-2.5"), 4, 3).hex() == "fffffffffffffffb"
    assert lvfxp.unpack_fxp(bytes.fromhex("fffffffffffffffb"), 4, 3) == Decimal("-2.5")
    assert lvfxp.pack_fxp_compact(Decimal("-2.5"), 4, 3) == b"\x0b"
    assert lvfxp.unpack_fxp_compact(b"\x0b", 4, 3) == Decimal("-2.5")


def test_array_form_is_count_then_flattened_elements() -> None:
    spec = FxpSpec(6, 3)
    values = [spec.decode(word) for word in range(64)]
    data = spec.pack_array(values)
    assert data[:4] == (64).to_bytes(4, "big")
    assert data[4:] == b"".join(spec.pack(value) for value in values)
    assert spec.unpack_array(data) == values


def test_errors_form_the_promised_hierarchy() -> None:
    assert issubclass(FxpOverflowError, FxpError)
    assert issubclass(FxpError, ValueError)
    with pytest.raises(FxpOverflowError):
        lvfxp.to_fxp(Decimal("16"), 8, 5)
