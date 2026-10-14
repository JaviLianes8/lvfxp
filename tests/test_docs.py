"""The documentation is executable: every module's doctests pass and every name has one."""

from __future__ import annotations

import doctest
import importlib
import inspect
import pkgutil
import re
import shlex
import typing
from pathlib import Path

import pytest

import lvfxp
from lvfxp._cli import main

_MODULES = ["lvfxp"] + [
    f"lvfxp.{m.name}" for m in pkgutil.iter_modules(lvfxp.__path__) if m.name != "__main__"
]


@pytest.mark.parametrize("name", _MODULES)
def test_module_doctests_pass(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name))  # each example imports its names
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


_ROOT = Path(__file__).resolve().parents[1]
_GUIDE = (_ROOT / "GUIDE.md").read_text(encoding="utf-8")


def test_guide_examples_run_and_print_what_they_show() -> None:
    blocks = re.findall(r"```pycon\n(.*?)```", _GUIDE, re.S)
    assert len(blocks) >= 8
    parser, runner = doctest.DocTestParser(), doctest.DocTestRunner()
    session: dict[str, object] = {}  # one reader's session: later blocks reuse earlier names
    for number, block in enumerate(blocks):
        test = parser.get_doctest(block, session, f"GUIDE.md[{number}]", "GUIDE.md", 0)
        runner.run(test, clear_globs=False)
        session.update(test.globs)
    assert runner.summarize(verbose=False).failed == 0


def _guide_transcript() -> list[tuple[list[str], list[str]]]:
    shell = re.search(r"## Command line.*?```\n(.*?)```", _GUIDE, re.S)
    assert shell is not None
    runs: list[tuple[list[str], list[str]]] = []
    for line in shell.group(1).splitlines():
        if line.startswith("$ lvfxp "):
            runs.append((shlex.split(line)[2:], []))
        else:
            runs[-1][1].append(line)
    return runs


@pytest.mark.parametrize(("args", "expected"), _guide_transcript())
def test_guide_transcript_matches(
    capsys: pytest.CaptureFixture[str], args: list[str], expected: list[str]
) -> None:
    assert main(args) == 0
    assert capsys.readouterr().out.splitlines() == expected


@pytest.mark.parametrize("name", [n for n in lvfxp.__all__ if callable(getattr(lvfxp, n))])
def test_type_hints_resolve_at_run_time(name: str) -> None:
    target = getattr(lvfxp, name)
    typing.get_type_hints(target)
    for member in vars(target).values() if inspect.isclass(target) else []:
        function = member.fget if isinstance(member, property) else member
        if inspect.isfunction(function):
            typing.get_type_hints(function)
    if target is lvfxp.FxpSpec:
        for base in target.__mro__[1:-1]:
            for member in vars(base).values():
                function = member.fget if isinstance(member, property) else member
                if inspect.isfunction(function):
                    typing.get_type_hints(function)
