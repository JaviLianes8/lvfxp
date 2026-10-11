"""End to end tests that run the real installed ``lvfxp`` console script.

These need the package installed (``pip install -e .``) so the entry point exists. They
drive the actual executable through ``subprocess`` and check real stdout and exit codes.
"""

import shutil
import subprocess
import sys
import sysconfig
from decimal import Decimal
from pathlib import Path

import pytest


def _console_script() -> str:
    found = shutil.which("lvfxp")
    if found:
        return found
    name = "lvfxp.exe" if sys.platform == "win32" else "lvfxp"
    candidate = Path(sysconfig.get_path("scripts")) / name
    if candidate.exists():
        return str(candidate)
    pytest.skip("lvfxp console script not installed; run 'pip install -e .'")


LVFXP = _console_script()


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([LVFXP, *args], capture_output=True, text=True, check=False)


def test_version_prints_the_release() -> None:
    result = _run("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "lvfxp 0.2.0"


def test_encode_prints_the_flattened_hex() -> None:
    result = _run("encode", "15.875", "--wl", "8", "--iwl", "5")
    assert result.returncode == 0
    assert result.stdout.strip() == "7f"


def test_encode_word_flag_prints_the_integer() -> None:
    result = _run("encode", "-2.5", "--wl", "4", "--iwl", "3", "--word")
    assert result.returncode == 0
    assert result.stdout.strip() == "11"


def test_encode_clamp_saturates() -> None:
    result = _run("encode", "16", "--wl", "8", "--iwl", "5", "--clamp")
    assert result.returncode == 0
    assert result.stdout.strip() == "7f"


def test_decode_a_real_twos_complement_word() -> None:
    result = _run("decode", "80", "--wl", "8", "--iwl", "5")
    assert result.returncode == 0
    assert Decimal(result.stdout.strip()) == Decimal("-16")


def test_decode_word_flag_and_unsigned() -> None:
    result = _run("decode", "--word", "128", "--wl", "8", "--iwl", "5", "--unsigned")
    assert result.returncode == 0
    assert Decimal(result.stdout.strip()) == Decimal("16")


def test_cli_round_trip_through_the_executable() -> None:
    encoded = _run("encode", "-1", "--wl", "16", "--iwl", "16").stdout.strip()
    assert encoded == "ffff"
    decoded = _run("decode", encoded, "--wl", "16", "--iwl", "16").stdout.strip()
    assert Decimal(decoded) == Decimal("-1")


def test_overflow_error_goes_to_stderr_with_exit_one() -> None:
    result = _run("encode", "16", "--wl", "8", "--iwl", "5")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "lvfxp:" in result.stderr


def test_bad_hex_is_reported_on_stderr() -> None:
    result = _run("decode", "zz", "--wl", "8", "--iwl", "5")
    assert result.returncode == 1
    assert "not valid hex" in result.stderr


def test_help_lists_runnable_examples() -> None:
    result = _run("--help")
    assert result.returncode == 0
    assert "examples:" in result.stdout
    assert "lvfxp encode" in result.stdout
