"""Contracts for the survivors of a third independent mutation round."""

from __future__ import annotations

import doctest
import io
from collections.abc import Iterator
from contextlib import redirect_stdout
from decimal import Decimal

import pytest

from lvfxp import FxpError, FxpSpec, _layout
from lvfxp._cli import main


def test_resolution_keeps_the_spelling_of_an_exponent_delta() -> None:
    spec = FxpSpec(8, 8, delta="1E+3")
    assert (str(spec.resolution), str(FxpSpec(8, 8, delta="1E-3").resolution)) == ("1E+3", "0.001")


def test_delta_is_stored_as_the_validated_decimal() -> None:
    for given in ("0.1", 0.1, Decimal("0.1")):
        spec = FxpSpec(8, 8, delta=given)
        assert type(spec.delta) is Decimal and spec.delta == Decimal("0.1")
    assert FxpSpec(8, 8, delta="0.1") == FxpSpec(8, 8, delta=Decimal("0.1"))


def test_integer_word_length_type_error_names_that_field() -> None:
    with pytest.raises(FxpError, match=r"^integer_word_length must be an int, not float$"):
        FxpSpec(8, 5.0)  # type: ignore[arg-type]


class _Hooked(FxpSpec):
    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "hooked", True)


def test_the_constructor_runs_an_overridden_post_init() -> None:
    assert vars(_Hooked(8, 5))["hooked"] is True


def test_decode_accepts_the_most_negative_signed_code() -> None:
    assert FxpSpec(8, 5).decode(-128) == Decimal("-16")
    assert FxpSpec(1, 0).decode(-1) == Decimal("-0.5")
    with pytest.raises(FxpError):
        FxpSpec(8, 5).decode(-129)


def test_every_layout_method_doctest_runs_and_passes() -> None:
    parser, runner = doctest.DocTestParser(), doctest.DocTestRunner()
    for name in ("encode", "decode", "encode_many", "decode_many"):
        doc = getattr(_layout.Layout, name).__doc__ or ""
        runner.run(parser.get_doctest(doc, {}, name, None, 0))
    assert runner.summarize(verbose=False) == (0, 9)


class _InstanceIndex:
    def __init__(self) -> None:
        self.__index__ = lambda: 8


def test_an_instance_level_index_is_not_an_integer() -> None:
    with pytest.raises(FxpError, match="must be an int"):
        FxpSpec(_InstanceIndex(), 5)


class _Int(int):
    pass


def test_integer_fields_are_stored_as_plain_int() -> None:
    spec = FxpSpec(_Int(8), _Int(5))
    assert (type(spec.word_length), type(spec.integer_word_length)) == (int, int)


class _ClaimsStr:
    @property  # type: ignore[misc]
    def __class__(self) -> type:
        return str

    def __iter__(self) -> Iterator[int]:
        return iter([1, 2])


def test_a_faked_class_does_not_turn_an_iterable_into_text() -> None:
    assert FxpSpec(8, 5).encode_many(_ClaimsStr()) == [8, 16]


class _Sequence:
    def __getitem__(self, index: int) -> int:
        if index >= 2:
            raise IndexError(index)
        return index + 1


def test_a_sequence_protocol_object_is_iterable() -> None:
    assert FxpSpec(8, 5).encode_many(_Sequence()) == [8, 16]  # type: ignore[arg-type]
    assert FxpSpec(8, 5).decode_many(_Sequence()) == [Decimal("0.125"), Decimal("0.250")]  # type: ignore[arg-type]


class _InstanceIter:
    def __init__(self) -> None:
        self.__iter__ = lambda: iter([1])


def test_an_instance_level_iter_is_refused_with_fxperror() -> None:
    with pytest.raises(FxpError, match="must be an iterable"):
        FxpSpec(8, 5).encode_many(_InstanceIter())


class _LyingFloat(float):
    def __repr__(self) -> str:
        return "2.5"


class _LyingStr(str):
    def __str__(self) -> str:
        return "2.5"


def test_float_and_str_subclasses_are_read_by_their_real_value() -> None:
    spec = FxpSpec(8, 5)
    assert spec.encode(_LyingFloat(1.5)) == 12
    assert spec.encode(_LyingStr("1.5")) == 12
    assert spec.offset == 0 and FxpSpec(8, 5, offset=_LyingStr("1")).offset == 1


class _AlwaysEqual(str):
    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = str.__hash__


def test_a_rounding_name_is_compared_as_plain_text() -> None:
    # "0.1" is code 0.8: half-even gives 1, a lying comparison would pick ROUND_FLOOR (0)
    assert FxpSpec(8, 5).encode("0.1", rounding=_AlwaysEqual("ROUND_HALF_EVEN")) == 1


class _LyingByteArray(bytearray):
    def __bytes__(self) -> bytes:
        return b"\xff" * 8


def test_a_bytearray_subclass_is_read_by_its_stored_bytes() -> None:
    data = _LyingByteArray(bytes.fromhex("0000000000000008"))
    assert FxpSpec(8, 5).unpack(data) == Decimal("1")


def _cli(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(list(argv))
    return code, out.getvalue()


def test_info_shows_a_negative_offset() -> None:
    assert "offset: -1.5" in _cli("info", "--wl", "8", "--iwl", "5", "--offset", "-1.5")[1]


def test_decode_hex_tolerates_spaces_around_a_0x_prefix() -> None:
    assert _cli("decode", " 0x00000000000000ff ", "--wl", "8", "--iwl", "8", "--unsigned") == (
        0,
        "255\n",
    )


class _NoIndex:
    __index__ = None


class _NoIter:
    __iter__ = None


def test_types_that_disable_index_or_iter_are_refused_with_fxp_error() -> None:
    spec = FxpSpec(8, 5)
    for call in (
        lambda: FxpSpec(_NoIndex(), 5),  # type: ignore[arg-type]
        lambda: spec.decode(_NoIndex()),  # type: ignore[arg-type]
        lambda: spec.encode_many(_NoIter()),  # type: ignore[arg-type]
        lambda: spec.decode_many(_NoIter()),  # type: ignore[arg-type]
    ):
        with pytest.raises(FxpError):
            call()
