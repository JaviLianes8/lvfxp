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


def _closed(stream: str, *args: str) -> tuple[int, bytes]:
    command = [sys.executable, "-m", "lvfxp", *args]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_ENV)
    closed, kept = (
        (process.stdout, process.stderr)
        if stream == "stdout"
        else (
            process.stderr,
            process.stdout,
        )
    )
    assert closed is not None and kept is not None
    closed.close()
    text = kept.read()
    kept.close()
    return process.wait(timeout=60), text


def test_help_and_version_to_a_closed_pipe_exit_cleanly() -> None:
    for args in (["--help"], ["--version"]):
        code, err = _closed("stdout", *args)
        assert (code, b"Traceback" in err, b"Exception ignored" in err) == (1, False, False)


def test_errors_to_a_closed_stderr_keep_their_exit_codes() -> None:
    assert _closed("stderr", "encode", "nan", "--wl", "8", "--iwl", "5")[0] == 1
    assert _closed("stderr", "bogus")[0] == 2


def test_a_descriptor_closed_inside_the_process_does_not_give_exit_120() -> None:
    code = (
        "import os, sys, runpy; os.close({fd}); "
        "sys.argv = ['lvfxp'] + {args!r}; runpy.run_module('lvfxp', run_name='__main__')"
    )
    cases = [
        (1, ["encode", "1", "--wl", "8", "--iwl", "5"], 1),
        (2, ["encode", "nan", "--wl", "8", "--iwl", "5"], 1),
    ]
    for fd, args, expected in cases:
        command = [sys.executable, "-c", code.format(fd=fd, args=args)]
        result = subprocess.run(command, capture_output=True, env=_ENV, timeout=60)
        assert result.returncode == expected, (fd, result.returncode)
