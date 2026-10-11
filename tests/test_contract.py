"""The contract: every public name keeps its documented promise, end to end.

This asserts the whole library through its public surface, not isolated internals. The
``PUBLIC_API`` list is the agreed contract; the module and this list must agree exactly.
"""

import importlib.resources
from decimal import Decimal

import pytest

import lvfxp
from lvfxp import (
    FxpError,
    FxpOverflowError,
    FxpSpec,
    from_fxp,
    pack_fxp,
    to_fxp,
    unpack_fxp,
)

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "FxpError",
    "FxpOverflowError",
    "FxpSpec",
    "from_fxp",
    "pack_fxp",
    "to_fxp",
    "unpack_fxp",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvfxp.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvfxp.__all__:
        assert hasattr(lvfxp, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvfxp.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvfxp").joinpath("py.typed").is_file()


def test_to_fxp_and_from_fxp_round_trip_exactly() -> None:
    # Promise: integer word codec round-trips for signed and unsigned layouts.
    assert to_fxp(Decimal("15.875"), 8, 5) == 0x7F
    assert from_fxp(0x7F, 8, 5) == Decimal("15.875")
    assert to_fxp(Decimal("3.5"), 3, 2, signed=False) == 0b111


def test_pack_fxp_and_unpack_fxp_round_trip_through_bytes() -> None:
    # Promise: the flattened byte codec matches LabVIEW two's-complement big-endian words.
    assert pack_fxp(Decimal("-16"), 8, 5) == b"\x80"
    assert unpack_fxp(b"\x80", 8, 5) == Decimal("-16")
    assert pack_fxp(Decimal("-1"), 16, 16) == b"\xff\xff"


def test_fxpspec_exposes_resolution_range_and_batch() -> None:
    # Promise: the spec describes a layout and encodes, decodes, packs and batches on it.
    spec = FxpSpec(8, 5)
    assert spec.resolution == Decimal("0.125")
    assert (spec.min_value, spec.max_value) == (Decimal("-16"), Decimal("15.875"))
    assert spec.byte_length == 1
    assert spec.encode(Decimal("15.875")) == 0x7F
    assert spec.decode(0x7F) == Decimal("15.875")
    assert spec.unpack(spec.pack(Decimal("-2"))) == Decimal("-2")
    assert spec.decode_many(spec.encode_many([Decimal("1"), Decimal("-1")])) == [
        Decimal("1"),
        Decimal("-1"),
    ]


def test_errors_form_the_promised_hierarchy() -> None:
    # Promise: FxpOverflowError is an FxpError is a ValueError, raised on overflow.
    assert issubclass(FxpOverflowError, FxpError)
    assert issubclass(FxpError, ValueError)
    with pytest.raises(FxpOverflowError):
        to_fxp(Decimal("16"), 8, 5)
