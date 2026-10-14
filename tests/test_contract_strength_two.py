"""Contracts for the survivors of a second independent mutation round."""

from __future__ import annotations

import io
import sys
from decimal import ROUND_CEILING, Decimal
from fractions import Fraction

import pytest

import lvfxp._cli_io as cli_io
from lvfxp import (
    LV_TRUNCATE,
    FxpError,
    FxpSpec,
    pack_fxp,
    pack_fxp_compact,
    unpack_fxp_compact,
)
from lvfxp._cli import main


def _message(call: object, *args: object, **kwargs: object) -> str:
    with pytest.raises(FxpError) as caught:
        call(*args, **kwargs)  # type: ignore[operator]
    return str(caught.value)


def test_a_64_bit_integer_is_shown_whole_and_a_65_bit_one_by_size() -> None:
    assert _message(FxpSpec, 2**63, 0).endswith("got 9223372036854775808")
    assert _message(FxpSpec, 2**64, 0).endswith("got an integer of 65 bits")


def test_a_value_whose_repr_fails_is_named_by_its_type() -> None:
    class BadRepr:
        def __repr__(self) -> str:
            raise RuntimeError("no repr")

    text = _message(FxpSpec(8, 5).encode, 1, rounding=BadRepr())
    assert text == "unknown rounding mode a BadRepr object"


def test_a_bool_option_is_shown_as_a_bool() -> None:
    assert _message(FxpSpec(8, 5).encode, 1, rounding=True) == "unknown rounding mode True"


def test_an_integer_at_the_exponent_bound_is_accepted() -> None:
    assert FxpSpec(8, 8, offset=10**10000).offset == Decimal(10**10000)
    assert "exponent" in _message(FxpSpec, 8, 8, offset=10**10001)


def test_trailing_zeros_past_the_exponent_bound_are_refused() -> None:
    text = "1." + "0" * 10001  # adjusted exponent 0, exponent -10001
    assert "exponent" in _message(FxpSpec, 8, 8, offset=text)
    assert "exponent" in _message(FxpSpec(8, 8).encode, text)


def test_batch_calls_refuse_a_memoryview() -> None:
    with pytest.raises(FxpError):
        FxpSpec(8, 8).encode_many(memoryview(b"\x01"))
    with pytest.raises(FxpError):
        FxpSpec(8, 8).decode_many(memoryview(b"\x01"))


def test_a_tiny_resolution_plus_an_offset_decodes_exactly() -> None:
    value = FxpSpec(8, -92, offset=1).decode(1)
    assert Fraction(value) == 1 + Fraction(1, 2**100)


def test_a_long_type_name_is_cut_in_messages() -> None:
    wide = type("A" * 60, (), {})()
    text = _message(FxpSpec(8, 8).encode, wide)
    assert "A" * 40 + "..." in text
    assert "A" * 41 not in text


def test_decimal_subclasses_are_stored_as_plain_decimal() -> None:
    class Sub(Decimal):
        pass

    spec = FxpSpec(8, 8, delta=Sub("0.5"), offset=Sub(1))
    assert type(spec.offset) is Decimal
    assert type(spec.resolution) is Decimal


def test_option_errors_win_over_value_errors() -> None:
    text = _message(FxpSpec(8, 5).encode, "junk", rounding="bogus")
    assert text.startswith("unknown rounding mode")


def test_options_are_checked_even_for_an_empty_batch() -> None:
    spec = FxpSpec(8, 5)
    with pytest.raises(FxpError, match="rounding"):
        spec.encode_many([], rounding="bogus")
    with pytest.raises(FxpError, match="overflow"):
        spec.pack_array([], overflow="nope")
    with pytest.raises(FxpError, match="clamp"):
        spec.pack_array([], clamp="x")  # type: ignore[arg-type]


def test_unpack_refuses_a_word_one_past_the_signed_or_unsigned_range() -> None:
    with pytest.raises(FxpError):
        FxpSpec(8, 5).unpack(bytes.fromhex("0000000000000080"))
    with pytest.raises(FxpError):
        FxpSpec(8, 5, signed=False).unpack(bytes.fromhex("0000000000000100"))


def test_only_nine_bytes_get_the_overflow_status_hint() -> None:
    assert "9 bytes" in _message(FxpSpec(8, 5).unpack, bytes(9))
    assert "9 bytes" not in _message(FxpSpec(8, 5).unpack, bytes(10))


def test_the_compact_form_is_big_endian_over_several_bytes() -> None:
    spec = FxpSpec(12, 12, signed=False)
    assert spec.pack_compact(0x123) == b"\x01\x23"
    assert pack_fxp_compact(0x123, 12, 12, False) == b"\x01\x23"


def test_byte_forms_and_free_functions_pass_every_option_through() -> None:
    spec = FxpSpec(8, 5)
    assert spec.pack("0.1", rounding=LV_TRUNCATE) == bytes(8)
    assert pack_fxp("0.1", 8, 5, rounding=LV_TRUNCATE) == bytes(8)
    assert spec.pack_compact("0.01", rounding=ROUND_CEILING) == b"\x01"
    assert spec.pack_array([99], clamp=True) == bytes.fromhex("00000001000000000000007f")
    assert pack_fxp_compact(99, 8, 5, clamp=True) == b"\x7f"
    assert unpack_fxp_compact(b"\xff", 8, 8, signed=False) == 255


def test_cli_exits_one_when_the_reader_of_stdout_is_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    class Gone(io.TextIOBase):
        def write(self, text: str) -> int:
            raise BrokenPipeError(32, "Broken pipe")

    monkeypatch.setattr(sys, "stdout", Gone())
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    assert main(["encode", "1", "--wl", "8", "--iwl", "5"]) == 1


def test_cli_exits_one_on_a_closed_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    closed = io.StringIO()
    closed.close()
    monkeypatch.setattr(sys, "stdout", closed)
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    assert main(["encode", "1", "--wl", "8", "--iwl", "5"]) == 1


class _LateFailure(io.StringIO):
    """Accepts the write and its flush, then fails every later flush (a reader that left)."""

    flushes = 0

    def flush(self) -> None:
        self.flushes += 1
        if self.flushes > 1:
            raise BrokenPipeError(32, "Broken pipe")


@pytest.mark.parametrize(
    "argv", [["encode", "1", "--wl", "8", "--iwl", "5"], ["--version"]], ids=["data", "version"]
)
def test_a_failed_final_flush_silences_the_stream(
    monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(cli_io, "silence", calls.append)
    monkeypatch.setattr(sys, "stdout", _LateFailure())
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    assert main(argv) == 0
    assert calls == [sys.stdout]


def test_cli_accepts_an_upper_case_hex_prefix(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "0X7f", "--wl", "8", "--iwl", "5", "--compact"]) == 0
    assert capsys.readouterr().out == "15.875\n"


def test_cli_truncate_rounds_toward_negative_infinity(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["encode", "-0.1", "--wl", "8", "--iwl", "5", "--rounding", "truncate"]) == 0
    assert capsys.readouterr().out == "ffffffffffffffff\n"


def test_a_cut_usage_error_ends_with_an_ellipsis(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["encode", "1", "--wl", "x" * 500, "--iwl", "5"]) == 2
    last = capsys.readouterr().err.splitlines()[-1]
    assert last.endswith("...")
    assert len(last) <= len("lvfxp encode: error: ") + 303
