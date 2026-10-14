"""Every I8 value cast by a real LabVIEW 2026 into three fixed-point layouts.

``datalog_fixed_point_cast_i8_sweep.dat`` holds 256 records of the shipped example
``Fixed-Point Cast.vi``, one per ``I8 2`` value from -128 to 127 (see ``manifest.json``).
Integer to Fixed-Point Cast copies the low bits of the integer into each word, so every
word of ``<+/-,6,6>`` and ``<+,10,4>`` reachable from an I8, and every word of
``<+/-,8,8>``, appears here exactly as LabVIEW flattened it.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from lvfxp import FxpSpec

_FIXTURES = Path(__file__).parent / "fixtures" / "labview2026"
_SWEEP = _FIXTURES / "datalog_fixed_point_cast_i8_sweep.dat"
_RECORD, _HEADER = 44, 6
_FIELDS = {  # offset in the 44-byte panel record, layout
    "<+/-,6,6>": (18, FxpSpec(6, 6)),
    "<+,10,4>": (28, FxpSpec(10, 4, signed=False)),
    "<+/-,8,8>": (36, FxpSpec(8, 8)),
}


def _records() -> list[bytes]:
    data = _SWEEP.read_bytes()
    count = int.from_bytes(data[8:12], "big")
    assert data[:4] == b"DTLG" and count == 256
    start = len(data) - count * (_HEADER + _RECORD)
    return [
        data[at + _HEADER : at + _HEADER + _RECORD]
        for at in range(start, len(data), _HEADER + _RECORD)
    ]


def _expected(i8: int, wl: int, iwl: int, signed: bool) -> Fraction:
    word = i8 & ((1 << wl) - 1)
    coded = word - (1 << wl) if signed and word >> (wl - 1) else word
    return coded * Fraction(2) ** (iwl - wl)


def test_the_capture_is_the_file_the_manifest_describes() -> None:
    entry = json.loads((_FIXTURES / "manifest.json").read_text("utf-8"))["files"][_SWEEP.name]
    data = _SWEEP.read_bytes()
    assert (len(data), hashlib.sha256(data).hexdigest()) == (entry["size"], entry["sha256"])


def test_every_i8_cast_decodes_and_packs_back_to_labviews_bytes() -> None:
    records = _records()
    for i8, record in zip(range(-128, 128), records, strict=True):
        assert int.from_bytes(record[26:27], "big", signed=True) == i8
        for offset, spec in _FIELDS.values():
            raw = record[offset : offset + 8]
            value = spec.unpack(raw)
            wl, iwl, signed = spec.word_length, spec.integer_word_length, spec.signed
            assert Fraction(value) == _expected(i8, wl, iwl, signed), (i8, spec)
            assert spec.pack(value) == raw
            assert spec.decode(spec.encode(value)) == value


def test_the_sweep_covers_every_word_of_the_eight_bit_layout() -> None:
    offset, spec = _FIELDS["<+/-,8,8>"]
    seen = {spec.unpack(record[offset : offset + 8]) for record in _records()}
    assert seen == {Decimal(code) for code in range(-128, 128)}
