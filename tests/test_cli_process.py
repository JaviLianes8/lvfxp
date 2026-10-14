"""The command as a separate process: ``python -m lvfxp`` and a reader that goes away."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
_ENV = {**os.environ, "PYTHONPATH": _SRC}


def _module(*args: str) -> subprocess.Popen[bytes]:
    command = [sys.executable, "-m", "lvfxp", *args]
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_ENV)


def test_python_dash_m_runs_the_command() -> None:
    process = _module("encode", "15.875", "--wl", "8", "--iwl", "5")
    out, err = process.communicate(timeout=60)
    assert (process.returncode, out.strip(), err) == (0, b"000000000000007f", b"")


def test_a_reader_that_goes_away_gives_exit_one_without_a_traceback() -> None:
    process = _module("encode", "15.875", "--wl", "8", "--iwl", "5")
    assert process.stdout is not None
    process.stdout.close()
    assert process.stderr is not None
    err = process.stderr.read()
    process.stderr.close()
    process.wait(timeout=60)
    assert process.returncode in (0, 1)  # 0 when the output fit the pipe before it closed
    assert b"Traceback" not in err
