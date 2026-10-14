"""Contracts for the two survivors of the second blind mutation round's re-run."""

from __future__ import annotations

import io
import sys

import pytest

import lvfxp._cli_io as cli_io
from lvfxp import FxpSpec
from lvfxp._cli import main


class _FlushFails(io.StringIO):
    def flush(self) -> None:
        raise BrokenPipeError(32, "Broken pipe")


def test_only_the_stream_whose_flush_failed_is_silenced(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(cli_io, "silence", calls.append)
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    monkeypatch.setattr(sys, "stderr", _FlushFails())
    assert main(["encode", "1", "--wl", "8", "--iwl", "5"]) == 0
    assert calls == [sys.stderr]


def test_a_grouped_zero_with_a_huge_exponent_is_zero() -> None:
    text = "0_0e99999999999999999999"
    assert FxpSpec(8, 8).encode(text) == 0
    assert FxpSpec(8, 8, offset=text).offset == 0
