"""Bytes written by a real LabVIEW 2026 (26.3.1f1), not computed by this library.

The fixtures are front-panel datalog files LabVIEW wrote when running its shipped example
``examples/Numerics/Fixed-Point Cast.vi`` with logging at completion, driven through
LabVIEW's ActiveX server with the ``I8 2`` control set to -27, 100, -128 and 31. Each
file ends with the record of the front panel's nine objects, packed in this order without
padding (the order the file's own type map lists them):

  <+/-,6,3>  I8  <+,8,8>  U8  <+/-,6,6>  I8 2  Stop  <+,10,4>  <+/-,8,8>

Every fixed-point object takes 8 bytes and every I8, U8 and Boolean takes 1, so the
record is the last 44 bytes. The example casts ``I8 2`` into the last three fixed-point
indicators with Integer to Fixed-Point Cast, so their words are its low bits.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from lvfxp import FxpSpec

_FIXTURES = Path(__file__).parent / "fixtures" / "labview2026"
_RECORD = 44
_LAYOUT = [  # (name, size, spec or None for the 1-byte integers and the Boolean)
    ("<+/-,6,3>", 8, FxpSpec(6, 3)),
    ("I8", 1, None),
    ("<+,8,8>", 8, FxpSpec(8, 8, signed=False)),
    ("U8", 1, None),
    ("<+/-,6,6>", 8, FxpSpec(6, 6)),
    ("I8 2", 1, None),
    ("Stop", 1, None),
    ("<+,10,4>", 8, FxpSpec(10, 4, signed=False)),
    ("<+/-,8,8>", 8, FxpSpec(8, 8)),
]


def _record(path: Path) -> dict[str, bytes]:
    data = path.read_bytes()
    assert data[:4] == b"DTLG", "not a LabVIEW datalog file"
    record, fields, start = data[-_RECORD:], {}, 0
    for name, size, _ in _LAYOUT:
        fields[name] = record[start : start + size]
        start += size
    return fields


def _decoded(path: Path) -> dict[str, Decimal]:
    fields = _record(path)
    return {name: spec.unpack(fields[name]) for name, _, spec in _LAYOUT if spec is not None}


@pytest.mark.parametrize("i8", [-27, 100, -128, 31])
def test_casts_of_the_i8_control_decode_to_its_low_bits(i8: int) -> None:
    path = _FIXTURES / f"datalog_fixed_point_cast_i8_{'m' if i8 < 0 else 'p'}{abs(i8)}.dat"
    fields = _record(path)
    assert int.from_bytes(fields["I8 2"], "big", signed=True) == i8
    values = _decoded(path)
    low6 = i8 & 0x3F
    assert values["<+/-,6,6>"] == Decimal(low6 - 64 if low6 >= 32 else low6)
    assert values["<+,10,4>"] == Decimal(i8 & 0x3FF) / 64
    assert values["<+/-,8,8>"] == Decimal(i8)


def test_fixed_point_controls_match_their_integer_casts() -> None:
    # Fixed-Point to Integer Cast copies the word bits into the I8 and U8 indicators.
    fields = _record(_FIXTURES / "datalog_fixed_point_cast_i8_m27.dat")
    values = _decoded(_FIXTURES / "datalog_fixed_point_cast_i8_m27.dat")
    assert values["<+/-,6,3>"] == Decimal(int.from_bytes(fields["I8"], "big", signed=True)) / 8
    assert values["<+,8,8>"] == Decimal(fields["U8"][0])


def test_labview_bytes_are_reproduced_exactly_by_pack() -> None:
    for path in sorted(_FIXTURES.glob("*.dat")):
        fields = _record(path)
        for name, value in _decoded(path).items():
            spec = next(spec for label, _, spec in _LAYOUT if label == name)
            assert spec is not None
            assert spec.pack(value) == fields[name], (path.name, name)


def test_signed_words_are_sign_extended_and_unsigned_zero_extended() -> None:
    fields = _record(_FIXTURES / "datalog_fixed_point_cast_i8_m27.dat")
    assert fields["<+/-,6,6>"].hex() == "ffffffffffffffe5"  # -27, top bits all ones
    assert fields["<+,10,4>"].hex() == "00000000000003e5"  # top word bit set, still zeros
