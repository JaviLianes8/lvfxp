"""Specs survive pickling, including pickles written by lvfxp 0.3.0."""

from __future__ import annotations

import copy
import dataclasses
import pickle
from decimal import Decimal

import pytest

import lvfxp
from lvfxp import FxpSpec
from lvfxp._cli import main

# pickle.dumps(FxpSpec(8, 5), protocol=2) and
# pickle.dumps(FxpSpec(8, 8, False, Decimal("0.1"), Decimal(1)), protocol=4), as written by
# the lvfxp 0.3.0 release from PyPI.
_PICKLED_BY_0_3_0: dict[tuple[object, ...], str] = {
    (8, 5, True, None, Decimal(0)): (
        "8002636c766678702e5f737065630a467870537065630a7100298171017d710228580b000000776f"
        "72645f6c656e67746871034b085813000000696e74656765725f776f72645f6c656e67746871044b"
        "0558060000007369676e6564710588580500000064656c746171064e58060000006f666673657471"
        "0763646563696d616c0a446563696d616c0a7108580100000030710985710a52710b75622e"
    ),
    (8, 8, False, Decimal("0.1"), Decimal(1)): (
        "80049590000000000000008c0b6c766678702e5f73706563948c07467870537065639493942981947d"
        "94288c0b776f72645f6c656e677468944b088c13696e74656765725f776f72645f6c656e677468944b"
        "088c067369676e656494898c0564656c7461948c07646563696d616c948c07446563696d616c949394"
        "8c03302e3194859452948c066f666673657494680b8c0131948594529475622e"
    ),
}


@pytest.mark.parametrize("fields", list(_PICKLED_BY_0_3_0))
def test_a_spec_pickled_by_0_3_0_loads_and_works(fields: tuple[object, ...]) -> None:
    spec = pickle.loads(bytes.fromhex(_PICKLED_BY_0_3_0[fields]))
    fresh = FxpSpec(*fields)  # type: ignore[arg-type]
    assert spec == fresh
    assert (spec.resolution, spec.decode(5), spec.encode(fresh.decode(5))) == (
        fresh.resolution,
        fresh.decode(5),
        5,
    )


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_a_spec_round_trips_through_pickle_with_only_its_fields(protocol: int) -> None:
    spec = FxpSpec(64, -4096, offset="0.5")
    data = pickle.dumps(spec, protocol=protocol)
    assert b"_step" not in data
    assert b"_fractions" not in data
    loaded = pickle.loads(data)
    assert loaded == spec
    assert loaded.decode(1) == spec.decode(1)


def test_methods_of_the_public_class_pickle_and_name_it() -> None:
    for member in (FxpSpec.encode, FxpSpec.decode, FxpSpec.pack):
        assert pickle.loads(pickle.dumps(member)) is member
        assert member.__module__ == "lvfxp._spec"
    assert "annotations" not in dir(lvfxp)


def test_usage_errors_show_the_subcommand_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "--wl", "8", "--iwl", "5"]) == 2
    assert capsys.readouterr().err.startswith("usage: lvfxp decode ")


@dataclasses.dataclass(frozen=True)
class _Tagged(FxpSpec):
    tag: str = "x"


class _Fixed8(FxpSpec):
    def __init__(self, integer_word_length: int) -> None:
        super().__init__(8, integer_word_length)


def test_a_dataclass_subclass_is_validated_and_keeps_its_fields() -> None:
    tagged = _Tagged(8, 5, tag="a")
    assert (tagged.resolution, tagged.encode("15.875"), tagged.tag) == (Decimal("0.125"), 127, "a")
    with pytest.raises(lvfxp.FxpError):
        _Tagged(99, 5)
    loaded = pickle.loads(pickle.dumps(tagged))
    assert (type(loaded), loaded, loaded.tag) == (_Tagged, tagged, "a")
    assert loaded.decode(1) == Decimal("0.125")


def test_a_subclass_with_its_own_init_round_trips() -> None:
    spec = _Fixed8(5)
    loaded = pickle.loads(pickle.dumps(spec))
    assert (type(loaded), loaded, loaded.max_value) == (_Fixed8, spec, Decimal("15.875"))


@dataclasses.dataclass(frozen=True, slots=True)
class _Slotted(FxpSpec):
    extra: str = "e"


@dataclasses.dataclass(frozen=True)
class _OwnPostInit(FxpSpec):
    unit: str = "V"

    def __post_init__(self) -> None:  # does not call super(), as some 0.3.0 users wrote
        pass


class _Labelled(FxpSpec):
    def __init__(self, word_length: int, integer_word_length: int, label: str) -> None:
        super().__init__(word_length, integer_word_length)
        object.__setattr__(self, "label", label)


@pytest.mark.parametrize(
    "clone", [copy.copy, copy.deepcopy, lambda s: pickle.loads(pickle.dumps(s))]
)
def test_subclasses_copy_and_pickle_whole(clone: object) -> None:
    for spec in (_Slotted(8, 5, extra="x"), _Labelled(8, 5, "lab"), _OwnPostInit(8, 5)):
        twin = clone(spec)  # type: ignore[operator]
        assert (type(twin), twin, vars(twin)) == (type(spec), spec, vars(spec))
        assert (twin.resolution, twin.encode("15.875")) == (Decimal("0.125"), 127)


def test_a_subclass_that_skips_the_parent_post_init_still_computes() -> None:
    spec = _OwnPostInit(8, 5)
    assert (spec.resolution, spec.decode(0x80), spec.max_value) == (
        Decimal("0.125"),
        Decimal("-16.000"),
        Decimal("15.875"),
    )


def test_no_derived_state_is_stored_on_the_instance() -> None:
    assert set(vars(FxpSpec(8, 5))) == {
        "word_length",
        "integer_word_length",
        "signed",
        "delta",
        "offset",
    }
