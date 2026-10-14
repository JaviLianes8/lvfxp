"""The documentation is executable: every module's doctests pass and every name has one."""

from __future__ import annotations

import doctest
import importlib
import inspect
import pkgutil
import re

import pytest

import lvfxp

_MODULES = ["lvfxp"] + [f"lvfxp.{m.name}" for m in pkgutil.iter_modules(lvfxp.__path__)]
_GLOBALS = {name: getattr(lvfxp, name) for name in lvfxp.__all__}


@pytest.mark.parametrize("name", _MODULES)
def test_module_doctests_pass(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name), extraglobs=_GLOBALS)
    assert result.failed == 0


@pytest.mark.parametrize(
    "name", [n for n in lvfxp.__all__ if callable(getattr(lvfxp, n)) and n != "EncodeOptions"]
)
def test_every_public_callable_has_a_docstring_with_an_example(name: str) -> None:
    assert ">>>" in (getattr(lvfxp, name).__doc__ or ""), name


def test_encode_options_documents_an_example() -> None:
    assert ">>>" in (lvfxp.EncodeOptions.__doc__ or "")


@pytest.mark.parametrize(
    "name", [n for n, _ in inspect.getmembers(lvfxp.FxpSpec) if not n.startswith("_")]
)
def test_every_public_member_of_the_spec_has_an_example(name: str) -> None:
    member = inspect.getattr_static(lvfxp.FxpSpec, name)
    if callable(member) or isinstance(member, property):
        assert ">>>" in (member.__doc__ or ""), name


def test_the_doctests_cover_every_public_name() -> None:
    finder = doctest.DocTestFinder()
    examples = "".join(
        example.source
        for module in _MODULES
        for test in finder.find(importlib.import_module(module))
        for example in test.examples
    )
    for name in lvfxp.__all__:
        assert re.search(rf"\b{name}\b", examples), name
