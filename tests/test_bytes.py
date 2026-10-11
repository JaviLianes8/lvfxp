from decimal import Decimal

import pytest

from lvfxp import FxpError, FxpSpec, pack_fxp, unpack_fxp

# Real LabVIEW flattened words: the two's-complement coded integer, big-endian, in the
# whole bytes LabVIEW uses. Each row is (hex, word_length, integer_word_length, signed,
# exact value). These are hand-computed from the datatype, not round-tripped shortcuts.
FIXTURES = [
    ("7f", 8, 5, True, Decimal("15.875")),  # largest signed <8,5>, resolution 0.125
    ("80", 8, 5, True, Decimal("-16")),  # most negative signed <8,5>
    ("ff", 8, 5, True, Decimal("-0.125")),  # -1 code, one step below zero
    ("f8", 8, 5, True, Decimal("-1")),  # -8 code times 0.125
    ("00", 8, 5, True, Decimal("0")),
    ("ffff", 16, 16, True, Decimal("-1")),  # pure signed 16-bit integer
    ("012c", 16, 16, True, Decimal("300")),
    ("7fff", 16, 16, True, Decimal("32767")),
    ("8000", 16, 16, True, Decimal("-32768")),
    ("ff", 8, 8, False, Decimal("255")),  # unsigned byte integer
    ("0b", 4, 3, True, Decimal("-2.5")),  # 0b1011 two's complement, resolution 0.5
]


@pytest.mark.parametrize(("hex_word", "wl", "iwl", "signed", "value"), FIXTURES)
def test_unpack_matches_the_flattened_word(
    hex_word: str, wl: int, iwl: int, signed: bool, value: Decimal
) -> None:
    assert unpack_fxp(bytes.fromhex(hex_word), wl, iwl, signed) == value


@pytest.mark.parametrize(("hex_word", "wl", "iwl", "signed", "value"), FIXTURES)
def test_pack_rebuilds_the_flattened_word(
    hex_word: str, wl: int, iwl: int, signed: bool, value: Decimal
) -> None:
    assert pack_fxp(value, wl, iwl, signed) == bytes.fromhex(hex_word)


def test_byte_length_rounds_up_to_whole_bytes() -> None:
    assert FxpSpec(8, 5).byte_length == 1
    assert FxpSpec(12, 6).byte_length == 2
    assert FxpSpec(1, 0).byte_length == 1
    assert FxpSpec(65, 1).byte_length == 9


def test_pack_unpack_round_trips_every_non_aligned_word() -> None:
    spec = FxpSpec(12, 6)
    for word in range(1 << 12):
        value = spec.decode(word)
        assert spec.unpack(spec.pack(value)) == value


def test_unpack_ignores_sign_extension_above_the_word() -> None:
    # 0b1011 in a 4-bit signed word is -2.5; a producer may sign-extend it to a full byte.
    assert FxpSpec(4, 3).unpack(bytes.fromhex("fb")) == Decimal("-2.5")
    assert FxpSpec(4, 3).unpack(bytes.fromhex("0b")) == Decimal("-2.5")


def test_unpack_rejects_the_wrong_byte_count() -> None:
    with pytest.raises(FxpError):
        unpack_fxp(b"\x00\x00", 8, 5)


def test_pack_saturates_when_asked() -> None:
    assert pack_fxp(Decimal("16"), 8, 5, clamp=True) == b"\x7f"


def test_batch_helpers_reuse_the_layout() -> None:
    spec = FxpSpec(8, 5)
    words = spec.encode_many([Decimal("0"), Decimal("15.875"), Decimal("-16")])
    assert words == [0, 0x7F, 0x80]
    assert spec.decode_many(words) == [Decimal("0"), Decimal("15.875"), Decimal("-16")]
