"""Real end-to-end: build a wheel, pip-install it into a throwaway venv, run its ``lvfxp``.

No imports of the CLI module and no mocks: every test shells out to the console script pip
generated inside a fresh virtual environment that shares nothing with the test runner.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import venv
from decimal import Decimal
from pathlib import Path

import pytest

import lvfxp

_ROOT = Path(__file__).resolve().parents[1]
_CAPTURE = _ROOT / "tests" / "fixtures" / "labview2026" / "datalog_fixed_point_cast_i8_m27.dat"


@pytest.fixture(scope="module")
def script(tmp_path_factory: pytest.TempPathFactory) -> str:
    wheels = tmp_path_factory.mktemp("wheels")
    build = [sys.executable, "-m", "pip", "wheel", "--quiet", "--no-deps"]
    if importlib.util.find_spec("hatchling") is not None:
        build.append("--no-build-isolation")
    subprocess.run([*build, "-w", str(wheels), str(_ROOT)], check=True, timeout=600)
    (wheel,) = wheels.glob("lvfxp-*.whl")
    env_dir = tmp_path_factory.mktemp("venv")
    venv.EnvBuilder(with_pip=True).create(env_dir)
    scripts = env_dir / ("Scripts" if os.name == "nt" else "bin")
    install = [str(scripts / "python"), "-m", "pip", "install", "--quiet", "--no-index"]
    subprocess.run([*install, "--no-deps", str(wheel)], check=True, timeout=600)
    where = [str(scripts / "python"), "-c", "import lvfxp; print(lvfxp.__file__)"]
    location = subprocess.run(where, check=True, capture_output=True, text=True, cwd=env_dir)
    assert Path(location.stdout.strip()).resolve().is_relative_to(env_dir.resolve())
    found = shutil.which("lvfxp", path=str(scripts))
    assert found is not None, "pip did not install the lvfxp console script"
    return found


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([script, *args], capture_output=True, text=True, timeout=60)


def test_version_comes_from_the_installed_package(script: str) -> None:
    result = _run(script, "--version")
    assert (result.returncode, result.stdout.strip()) == (0, f"lvfxp {lvfxp.__version__}")


def test_help_shows_runnable_examples(script: str) -> None:
    result = _run(script, "--help")
    assert result.returncode == 0
    for text in ("examples:", "lvfxp encode", "lvfxp decode", "lvfxp info", "--compact"):
        assert text in result.stdout


def test_decodes_the_bytes_labview_wrote(script: str) -> None:
    record = _CAPTURE.read_bytes()[-44:]
    signed6 = record[18:26].hex()  # <+/-,6,6> holding -27
    unsigned10 = record[28:36].hex()  # <+,10,4> holding the low 10 bits of -27
    first = _run(script, "decode", signed6, "--wl", "6", "--iwl", "6")
    second = _run(script, "decode", unsigned10, "--wl", "10", "--iwl", "4", "--unsigned")
    assert (first.returncode, first.stdout.strip()) == (0, "-27")
    assert (second.returncode, second.stdout.strip()) == (0, "15.578125")


def test_encode_reproduces_the_labview_bytes(script: str) -> None:
    record = _CAPTURE.read_bytes()[-44:]
    result = _run(script, "encode", "15.578125", "--wl", "10", "--iwl", "4", "--unsigned")
    assert (result.returncode, result.stdout.strip()) == (0, record[28:36].hex())


def test_round_trip_through_the_executable(script: str) -> None:
    encoded = _run(script, "encode", "-1.25", "--wl", "16", "--iwl", "8").stdout.strip()
    assert encoded == "fffffffffffffec0"
    decoded = _run(script, "decode", encoded, "--wl", "16", "--iwl", "8").stdout.strip()
    assert Decimal(decoded) == Decimal("-1.25")


def test_compact_and_info_commands(script: str) -> None:
    assert _run(script, "encode", "-1", "--wl", "16", "--iwl", "16", "--compact").stdout == (
        "ffff\n"
    )
    info = _run(script, "info", "--wl", "8", "--iwl", "5")
    assert info.returncode == 0
    assert "resolution: 0.125" in info.stdout


def test_errors_exit_one_on_stderr_and_bad_usage_exits_two(script: str) -> None:
    overflow = _run(script, "encode", "16", "--wl", "8", "--iwl", "5")
    assert (overflow.returncode, overflow.stdout) == (1, "")
    assert overflow.stderr.startswith("lvfxp: ")
    assert _run(script, "decode", "80", "--wl", "8", "--iwl", "5").returncode == 1
    assert _run(script, "frobnicate").returncode == 2
