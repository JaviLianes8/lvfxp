"""Contracts for mutations that an independent mutation round found the suite did not catch."""

from __future__ import annotations

from decimal import (
    ROUND_05UP,
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
)
from fractions import Fraction

import pytest

import lvfxp
from lvfxp import FxpError, FxpSpec, to_fxp, unpack_fxp
from lvfxp._cli import main

_MODES = [
    ROUND_05UP,
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
]


def test_exponent_exactly_at_the_bound_is_accepted() -> None:
    assert FxpSpec(8, 5, offset="1e10000").offset == Decimal("1e10000")
    assert FxpSpec(8, 5, offset="1e-10000").offset == Decimal("1e-10000")
    with pytest.raises(FxpError, match="exponent beyond"):
        FxpSpec(8, 5, offset="1e10001")


def test_a_zero_with_a_huge_exponent_is_plain_zero() -> None:
    spec = FxpSpec(8, 5, offset="0e-20000")
    assert str(spec.decode(0x80)) == "-16.000"
    assert str(spec.offset) == "0"


def test_decode_is_exact_with_a_large_offset_and_fine_resolution() -> None:
    value = FxpSpec(8, 5, offset="1e30").decode(1)
    assert Fraction(value) == Fraction(10**30) + Fraction(1, 8)
    value = FxpSpec(64, -60, offset="1e-40").decode(1)
    assert Fraction(value) == Fraction(1, 10**40) + Fraction(1, 2**124)


@pytest.mark.parametrize("mode", _MODES)
def test_every_decimal_rounding_mode_matches_decimal_itself(mode: str) -> None:
    spec = FxpSpec(16, 16)
    for tenths in range(-200, 201):
        value = Decimal(tenths) / 10
        expected = int(value.quantize(Decimal(1), rounding=mode))
        assert spec.encode(value, rounding=mode) == expected % (1 << 16), (value, mode)


class _EqualsAnything:
    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = object.__hash__


def test_overflow_must_be_a_real_string() -> None:
    with pytest.raises(FxpError, match="overflow must be one of"):
        to_fxp(99, 8, 5, overflow=_EqualsAnything())  # type: ignore[arg-type]


def test_array_count_bound_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lvfxp._flat, "_MAX_COUNT", 2)
    assert len(FxpSpec(8, 5).pack_array([0, 0])) == 4 + 16
    with pytest.raises(FxpError, match="at most 2 elements"):
        FxpSpec(8, 5).pack_array([0, 0, 0])


@pytest.mark.parametrize("raw", ["ffffffffffffff7f", "ffffffffffffff00", "fffffffffffffe80"])
def test_unpack_refuses_negatives_that_are_not_a_sign_extension(raw: str) -> None:
    with pytest.raises(FxpError, match="not a signed 8-bit word"):
        unpack_fxp(bytes.fromhex(raw), 8, 5)


def test_pack_array_and_pack_compact_take_the_encode_options() -> None:
    spec = FxpSpec(8, 5)
    assert spec.pack_array([99, -99], overflow="saturate") == (
        bytes.fromhex("00000002") + spec.pack(99, clamp=True) + spec.pack(-99, clamp=True)
    )
    assert spec.pack_array(["0.0625"], rounding=lvfxp.LV_ROUND_HALF_UP)[-1] == 1
    assert spec.pack_compact(99, clamp=True) == b"\x7f"
    assert spec.pack_compact(16, overflow="wrap") == b"\x80"
    assert spec.pack_compact("-0.0625", rounding=lvfxp.LV_TRUNCATE) == b"\xff"


def test_cli_decodes_word_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "--word", "0", "--wl", "8", "--iwl", "5"]) == 0
    assert capsys.readouterr().out == "0\n"


def test_cli_turns_any_value_error_into_exit_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*args: object, **kwargs: object) -> int:
        raise ValueError("x" * 5000)

    monkeypatch.setattr(FxpSpec, "encode", boom)
    assert main(["encode", "1", "--wl", "8", "--iwl", "5", "--word"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("lvfxp: xxx")
    assert len(err) < 400


def test_cli_usage_errors_do_not_echo_huge_numbers(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "--word", "9" * 5000, "--wl", "8", "--iwl", "5"]) == 2
    assert len(capsys.readouterr().err) < 1000
