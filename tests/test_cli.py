"""In-process tests of the command line parser and output (the real script: e2e test)."""

from __future__ import annotations

import pytest

from lvfxp._cli import _EXAMPLES, main


def _run(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = main(list(args))
    out, err = capsys.readouterr()
    return code, out.strip(), err.strip()


def _examples() -> list[tuple[list[str], str]]:
    rows = []
    for line in _EXAMPLES.splitlines():
        if line.startswith("  lvfxp ") and "->" in line:
            command, expected = line.split("->")
            rows.append((command.split()[1:], expected.strip()))
    return rows


@pytest.mark.parametrize(("args", "expected"), _examples())
def test_every_help_example_prints_what_it_claims(
    capsys: pytest.CaptureFixture[str], args: list[str], expected: str
) -> None:
    assert _run(capsys, *args) == (0, expected, "")


def test_info_describes_the_layout(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(capsys, "info", "--wl", "10", "--iwl", "4", "--unsigned")
    assert code == 0
    assert out.splitlines() == [
        "layout: <+, 10, 4>",
        "resolution: 0.015625",
        "minimum: 0",
        "maximum: 15.984375",
        "flattened bytes: 8",
        "compact bytes: 2",
    ]


def test_decode_prints_plain_exact_digits(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(capsys, "decode", "--word", "1", "--wl", "64", "--iwl", "0")
    assert code == 0
    assert out == "0.0000000000000000000542101086242752217003726400434970855712890625"


def test_clamp_is_kept_as_an_alias(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(capsys, "encode", "99", "--wl", "8", "--iwl", "5", "--clamp")[1] == (
        "000000000000007f"
    )


def test_hex_accepts_prefix_spaces_and_underscores(capsys: pytest.CaptureFixture[str]) -> None:
    out = _run(capsys, "decode", "0xffff ffff_ffff ff80", "--wl", "8", "--iwl", "5")[1]
    assert out == "-16"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["encode", "16", "--wl", "8", "--iwl", "5"], "outside"),
        (["encode", "abc", "--wl", "8", "--iwl", "5"], "not a number"),
        (["encode", "1", "--wl", "65", "--iwl", "5"], "between 1 and 64"),
        (["decode", "zz", "--wl", "8", "--iwl", "5"], "not valid hex"),
        (["decode", "80", "--wl", "8", "--iwl", "5"], "8 bytes, got 1"),
        (["decode", "00" * 9, "--wl", "8", "--iwl", "5"], "overflow status"),
        (["decode", "00000000000000ff", "--wl", "8", "--iwl", "5"], "extended"),
        (["decode", "--wl", "8", "--iwl", "5"], "use --word"),
        (["decode", "7f", "--word", "1", "--wl", "8", "--iwl", "5"], "not both"),
        (["encode", "1", "--wl", "8", "--iwl", "5", "--clamp", "--overflow", "wrap"], "wrap"),
    ],
)
def test_data_errors_go_to_stderr_with_exit_one(
    capsys: pytest.CaptureFixture[str], args: list[str], message: str
) -> None:
    code, out, err = _run(capsys, *args)
    assert (code, out) == (1, "")
    assert err.startswith("lvfxp: ")
    assert message in err


def test_usage_errors_exit_two(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["encode", "1", "--wl", "8", "--iwl", "5", "--word", "--compact"])
    assert raised.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


def test_info_names_an_explicit_delta_and_offset(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(
        capsys, "info", "--wl", "8", "--iwl", "5", "--delta", "0.1", "--offset", "1"
    )
    assert code == 0
    assert out.splitlines()[:3] == [
        "layout: <+/-, 8> with an explicit delta",
        "offset: 1",
        "resolution: 0.1",
    ]


def test_double_dash_passes_a_negative_exponent_value(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(capsys, "encode", "--wl", "8", "--iwl", "5", "--", "-1e0") == (
        0,
        "fffffffffffffff8",
        "",
    )


def test_out_of_bound_input_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(capsys, "info", "--wl", "8", "--iwl", "-100000000")[0] == 1
    assert _run(capsys, "encode", "1e999999999", "--wl", "8", "--iwl", "5")[0] == 1
