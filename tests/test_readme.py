"""The README's examples run, and its command line transcript matches the real output."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lvfxp._cli import main

_README = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("block", re.findall(r"```python\n(.*?)```", _README, re.S))
def test_python_examples_run(block: str) -> None:
    exec(compile(block, "README.md", "exec"), {})


def _transcript() -> list[tuple[list[str], list[str]]]:
    shell = re.search(r"## Command line.*?```\n(.*?)```", _README, re.S)
    assert shell is not None
    runs: list[tuple[list[str], list[str]]] = []
    for line in shell.group(1).splitlines():
        if line.startswith("$ lvfxp "):
            runs.append((line.split()[2:], []))
        else:
            runs[-1][1].append(line)
    return runs


@pytest.mark.parametrize(("args", "expected"), _transcript())
def test_command_line_transcript_matches(
    capsys: pytest.CaptureFixture[str], args: list[str], expected: list[str]
) -> None:
    assert main(args) == 0
    assert capsys.readouterr().out.splitlines() == expected
