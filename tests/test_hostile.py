"""Hostile input: messages stay short, the caller's decimal context is ignored, buffers are read
as raw bytes, and every refusal is an FxpError."""

from __future__ import annotations

import array
import decimal
from decimal import Decimal

import pytest

from lvfxp import FxpError, FxpSpec, from_fxp, to_fxp, unpack_fxp
from lvfxp._cli import main


@pytest.mark.parametrize(
    "call",
    [
        lambda: to_fxp("x" * 100_000, 8, 5),
        lambda: to_fxp("1" * 100_000, 8, 5),
        lambda: from_fxp(10**4000, 8, 5),
        lambda: from_fxp(-(10**4000), 8, 5),
        lambda: FxpSpec(10**4000, 5),
        lambda: to_fxp(10**20000, 8, 5),
        lambda: FxpSpec(8, 5).encode([0] * 100_000),  # type: ignore[arg-type]
        lambda: FxpSpec(8, 5).unpack("z" * 100_000),  # type: ignore[arg-type]
    ],
)
def test_error_messages_stay_short(call: object) -> None:
    with pytest.raises(FxpError) as raised:
        call()  # type: ignore[operator]
    assert len(str(raised.value)) < 200


def test_a_value_is_shown_whole_up_to_the_limit_and_cut_after_it() -> None:
    with pytest.raises(FxpError, match=r"'a{38}'$"):
        to_fxp("a" * 38, 8, 5)
    with pytest.raises(FxpError, match=r"\.\.\. \(41 characters\)"):
        to_fxp("a" * 39, 8, 5)


def test_huge_integers_are_described_not_printed() -> None:
    with pytest.raises(FxpError, match="an integer of 65 bits"):
        from_fxp(2**64, 8, 5)
    with pytest.raises(FxpError, match=str(2**63)):
        from_fxp(2**63, 8, 5)


def test_huge_integer_values_are_refused_at_once() -> None:
    with pytest.raises(FxpError, match="exponent"):
        to_fxp(1 << 200_000, 8, 5, overflow="saturate")


@pytest.mark.parametrize(
    "context",
    [
        decimal.Context(prec=3),
        decimal.Context(Emax=10, Emin=-10),
        decimal.Context(traps=[]),
        decimal.Context(rounding=decimal.ROUND_UP, prec=5),
    ],
)
def test_the_callers_decimal_context_changes_nothing(context: decimal.Context) -> None:
    with decimal.localcontext(context):
        tiny = from_fxp(1, 64, 0, signed=False)
        assert (
            format(tiny, "f")
            == "0.0000000000000000000542101086242752217003726400434970855712890625"
        )
        assert FxpSpec(64, 64, signed=False).max_value == 2**64 - 1
        with pytest.raises(FxpError, match="not a number"):
            to_fxp("abc", 8, 5)
        assert not context.flags[decimal.InvalidOperation]


def test_buffers_are_read_as_their_raw_bytes() -> None:
    raw = bytes.fromhex("ffffffffffffff80")
    assert unpack_fxp(memoryview(array.array("H", raw)), 8, 5) == -16
    assert unpack_fxp(bytearray(raw), 8, 5) == -16
    released = memoryview(raw)
    released.release()
    with pytest.raises(FxpError, match="released"):
        unpack_fxp(released, 8, 5)


class _LyingBytes(bytes):
    def __len__(self) -> int:
        return 8

    def __bytes__(self) -> bytes:
        return bytes(8)


def test_a_bytes_subclass_cannot_lie_about_itself() -> None:
    with pytest.raises(FxpError, match="got 9"):
        unpack_fxp(_LyingBytes(bytes(9)), 8, 5)
    assert unpack_fxp(_LyingBytes(bytes.fromhex("fffffffffffffff8")), 8, 5) == -1


class _Index:
    def __init__(self, value: int) -> None:
        self.value = value

    def __index__(self) -> int:
        return self.value


def test_any_integer_type_is_accepted_and_stored_as_int() -> None:
    spec = FxpSpec(_Index(8), _Index(5))  # type: ignore[arg-type]
    assert (type(spec.word_length), type(spec.integer_word_length)) == (int, int)
    assert spec == FxpSpec(8, 5)
    assert spec.decode(_Index(0x80)) == -16  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [8.0, Decimal(8), "8", True, None])
def test_non_integers_are_refused_for_integer_fields(bad: object) -> None:
    with pytest.raises(FxpError, match="word_length must be an int"):
        FxpSpec(bad, 5)  # type: ignore[arg-type]


def test_cli_does_not_echo_huge_bad_input(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "zz" * 50_000, "--wl", "8", "--iwl", "5"]) == 1
    assert main(["encode", "q" * 100_000, "--wl", "8", "--iwl", "5"]) == 1
    err = capsys.readouterr().err
    assert len(err) < 400


def test_option_and_overflow_messages_stay_short() -> None:
    with pytest.raises(FxpError) as raised:
        to_fxp(1, 8, 5, rounding="r" * 10_000)
    assert len(str(raised.value)) < 200
    with pytest.raises(FxpError) as raised:
        to_fxp(1, 8, 5, overflow="o" * 10_000)
    assert len(str(raised.value)) < 200
    with pytest.raises(FxpError, match="an integer of 33906 bits") as raised:
        to_fxp("1e9000", 8, -4000)
    assert len(str(raised.value)) < 200
