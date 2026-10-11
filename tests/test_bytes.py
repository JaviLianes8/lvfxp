from decimal import Decimal

import pytest

from lvfxp import (
    FLATTENED_SIZE,
    FxpError,
    FxpSpec,
    pack_fxp,
    pack_fxp_compact,
    unpack_fxp,
    unpack_fxp_compact,
)

# LabVIEW's flattened form: the word in the low bits of 8 big-endian bytes, sign extended
# when signed and zero extended when unsigned. Rows: (hex, wl, iwl, signed, exact value).
FLATTENED = [
    ("000000000000007f", 8, 5, True, Decimal("15.875")),
    ("ffffffffffffff80", 8, 5, True, Decimal("-16")),
    ("ffffffffffffffff", 8, 5, True, Decimal("-0.125")),
    ("0000000000000000", 8, 5, True, Decimal("0")),
    ("ffffffffffffffe0", 6, 3, True, Decimal("-4")),  # captured from LabVIEW 2026
    ("00000000000003e5", 10, 4, False, Decimal("15.578125")),  # captured, zero extended
    ("000000000000002d", 8, 8, False, Decimal("45")),  # captured
    ("fffffffffffffffb", 4, 3, True, Decimal("-2.5")),
    ("000000000000012c", 16, 16, True, Decimal("300")),
    ("7fffffffffffffff", 64, 64, True, Decimal(2**63 - 1)),
    ("8000000000000000", 64, 64, True, Decimal(-(2**63))),
    ("ffffffffffffffff", 64, 64, False, Decimal(2**64 - 1)),
]


@pytest.mark.parametrize(("hex_word", "wl", "iwl", "signed", "value"), FLATTENED)
def test_unpack_reads_labviews_flattened_form(
    hex_word: str, wl: int, iwl: int, signed: bool, value: Decimal
) -> None:
    assert unpack_fxp(bytes.fromhex(hex_word), wl, iwl, signed) == value


@pytest.mark.parametrize(("hex_word", "wl", "iwl", "signed", "value"), FLATTENED)
def test_pack_writes_labviews_flattened_form(
    hex_word: str, wl: int, iwl: int, signed: bool, value: Decimal
) -> None:
    assert pack_fxp(value, wl, iwl, signed) == bytes.fromhex(hex_word)


def test_flattened_size_is_always_eight_bytes() -> None:
    assert FLATTENED_SIZE == 8
    for wl in (1, 8, 12, 33, 64):
        assert FxpSpec(wl, 0).byte_length == 8
        assert len(FxpSpec(wl, 0).pack(0)) == 8


def test_unpack_rejects_high_bits_that_are_not_the_extension() -> None:
    with pytest.raises(FxpError, match="extended to 64 bits"):
        unpack_fxp(bytes.fromhex("00000000000000ff"), 8, 5)  # 0xff unsigned, not -1
    with pytest.raises(FxpError):
        unpack_fxp(bytes.fromhex("ffffffffffffffff"), 8, 5, signed=False)
    with pytest.raises(FxpError):
        unpack_fxp(bytes.fromhex("000000000000000b"), 4, 3)  # 4-bit -5 not sign extended


def test_unpack_rejects_the_wrong_size_and_explains_nine_bytes() -> None:
    with pytest.raises(FxpError, match="got 1"):
        unpack_fxp(b"\x80", 8, 5)
    with pytest.raises(FxpError, match="overflow status"):
        unpack_fxp(bytes(9), 8, 5)


def test_compact_form_is_ceil_word_length_over_eight_bytes() -> None:
    assert FxpSpec(8, 5).compact_byte_length == 1
    assert FxpSpec(12, 6).compact_byte_length == 2
    assert FxpSpec(64, 1).compact_byte_length == 8
    assert pack_fxp_compact(Decimal("-16"), 8, 5) == b"\x80"
    assert pack_fxp_compact(Decimal("-2.5"), 4, 3) == b"\x0b"
    assert unpack_fxp_compact(b"\xff\xff", 16, 16) == Decimal("-1")


def test_compact_unpack_ignores_bits_above_the_word() -> None:
    assert FxpSpec(4, 3).unpack_compact(bytes.fromhex("fb")) == Decimal("-2.5")
    assert FxpSpec(4, 3).unpack_compact(bytes.fromhex("0b")) == Decimal("-2.5")
    with pytest.raises(FxpError):
        FxpSpec(8, 5).unpack_compact(b"\x00\x00")


def test_pack_takes_the_encode_options() -> None:
    assert pack_fxp(Decimal("16"), 8, 5, clamp=True) == bytes.fromhex("000000000000007f")
    assert pack_fxp(Decimal("16"), 8, 5, overflow="wrap") == bytes.fromhex("ffffffffffffff80")


def test_array_is_a_count_then_eight_byte_elements() -> None:
    spec = FxpSpec(8, 5)
    data = spec.pack_array([Decimal("1"), Decimal("-1")])
    assert data.hex() == "00000002" + "0000000000000008" + "fffffffffffffff8"
    assert spec.unpack_array(data) == [Decimal("1"), Decimal("-1")]
    assert spec.pack_array([]) == b"\x00\x00\x00\x00"
    assert spec.unpack_array(b"\x00\x00\x00\x00") == []


def test_array_length_must_match_its_count() -> None:
    spec = FxpSpec(8, 5)
    with pytest.raises(FxpError):
        spec.unpack_array(b"\x00\x00\x00")
    with pytest.raises(FxpError):
        spec.unpack_array(bytes.fromhex("00000002") + bytes(8))
    with pytest.raises(FxpError):
        spec.unpack_array(bytes.fromhex("ffffffff"))


def test_batch_helpers_reuse_the_layout() -> None:
    spec = FxpSpec(8, 5)
    words = spec.encode_many([Decimal("0"), Decimal("15.875"), Decimal("-16")])
    assert words == [0, 0x7F, 0x80]
    assert spec.decode_many(words) == [Decimal("0"), Decimal("15.875"), Decimal("-16")]
    assert spec.encode_many([Decimal("99")], clamp=True) == [0x7F]
