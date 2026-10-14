"""Edge contracts added for mutations of the author's round that the suite first missed."""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

from lvfxp import FxpError, FxpSpec, _cli, to_fxp
from lvfxp._cli import main


def test_an_array_with_trailing_bytes_is_refused() -> None:
    spec = FxpSpec(8, 5)
    with pytest.raises(FxpError, match="needs 8 element bytes, got 16"):
        spec.unpack_array(bytes.fromhex("00000001") + bytes(16))


def test_the_array_count_is_read_as_a_signed_32_bit_integer() -> None:
    with pytest.raises(FxpError, match="array count -1 needs 0 element bytes"):
        FxpSpec(8, 5).unpack_array(bytes.fromhex("ffffffff"))


def test_an_unsigned_array_keeps_words_with_the_top_bit_set() -> None:
    spec = FxpSpec(10, 4, signed=False)
    data = bytes.fromhex("0000000100000000000003e5")
    assert spec.unpack_array(data) == [Decimal("15.578125")]
    assert spec.pack_array([Decimal("15.578125")]) == data


def test_a_long_digit_string_is_refused_for_its_size_not_saturated() -> None:
    with pytest.raises(FxpError, match="exponent"):
        to_fxp("1" * 10_002, 8, 5, overflow="saturate")
    assert to_fxp("9" * 300, 8, 5, overflow="saturate") == 127


def test_a_huge_integer_is_refused_before_any_conversion() -> None:
    value = 1 << 4_000_000
    start = time.perf_counter()
    with pytest.raises(FxpError, match="exponent"):
        to_fxp(value, 8, 5, overflow="saturate")
    assert time.perf_counter() - start < 0.5


def test_cli_half_up_sends_positive_ties_up(capsys: pytest.CaptureFixture[str]) -> None:
    args = ["encode", "0.0625", "--wl", "8", "--iwl", "5", "--word"]
    assert main([*args, "--rounding", "half-up"]) == 0
    assert main([*args, "--rounding", "half-even"]) == 0
    assert main([*args, "--rounding", "truncate"]) == 0
    assert capsys.readouterr().out.split() == ["1", "0", "0"]


def test_cli_cuts_any_long_error_message(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(_: object) -> str:
        raise ArithmeticError("x" * 5000)

    monkeypatch.setitem(_cli._COMMANDS, "info", explode)
    assert main(["info", "--wl", "8", "--iwl", "5"]) == 1
    assert capsys.readouterr().err.strip() == "lvfxp: " + "x" * 300
