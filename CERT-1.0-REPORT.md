# lvfxp 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0, e654fd6)
- [x] Real LabVIEW 2026 capture: every I8 value through `Fixed-Point Cast.vi` (item 7)
- [x] Baseline gates run on 0.3.0
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18): contracts and seeded oracle written; mutation round running
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19): first round done (b PASS; a, c, d FAIL, fixed); re-verification of a, b, c, d running at a8e90b4; e running
- [ ] Gates (item 15)
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Scorecard

| # | Item | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | API reviewed for stability | open | |
| 2 | `__all__` exact | open | |
| 3 | Docstrings with runnable examples, doctests pass | open | |
| 4 | Typed end to end | FAIL on 0.3.0 | `mypy --strict src tests`: `unpack` accepts a `memoryview` at run time but its signature says `bytes | bytearray` |
| 5 | Typed, documented, safe errors | open | |
| 6 | Contract asserts the full promise | open | |
| 7 | Real ground truth | in progress | five files written by LabVIEW 2026 on this PC (see below) |
| 8 | Real e2e incl. PyPI upgrade | open | |
| 9 | Seeded fuzz, no crash, hang or blow-up | open | |
| 10 | Every interpreter on this PC | open | |
| 11 | README | open | |
| 12 | CHANGELOG dated 1.0.0 | open | |
| 13 | pyproject | open | |
| 14 | sdist and wheel contents | open | |
| 15 | Gates exit 0 alone | open | |
| 16 | Independent reviewer | open | |
| 17 | PR, trace guard | open | |
| 18 | Mutation round | open | |
| 19 | Five QA lenses | open | |

## Ground truth (item 7)

`tests/fixtures/labview2026/` holds front-panel datalog files written by LabVIEW 2026
Community 26.3.1f1 on this PC from the shipped example `examples/Numerics/Fixed-Point
Cast.vi`, run headless through LabVIEW's ActiveX server; `manifest.json` records how each
file was made, its size and SHA-256. The four single-run files date from 0.3.0. On
2026-10-14 the example was run once for every `I8 2` value from -128 to 127, logging the 256
records to `datalog_fixed_point_cast_i8_sweep.dat`; `tests/test_real_labview_sweep.py`
decodes all three cast indicators of every record (`<+/-,6,6>`, `<+,10,4>`, `<+/-,8,8>`,
768 flattened words, every word of the 8-bit layout) against exact rational arithmetic and
packs each value back to LabVIEW's bytes.

Not capturable through the ActiveX server: setting or reading a fixed-point control
(`SetControlValue` leaves it at zero and `GetControlValue` reports a type mismatch), so
LabVIEW's rounding and overflow modes and the 72-bit overflow-status form could not be
captured with chosen values.

## API review (item 1)

The sixteen public names of 0.3.0 are kept with the same signatures and defaults. Changes for
1.0.0, all listed in CHANGELOG 1.0.0 and the guide's upgrade section:

- Integer arguments accept any `__index__` integer (NumPy integers) and are stored as `int`.
- Byte arguments are typed `bytes | bytearray | memoryview`, which 0.3.0 already accepted at
  run time (`mypy --strict` flagged its own test of that), and a `memoryview` is read as its
  raw bytes whatever its item format.
- Error messages are bounded (40 characters of a value, wide integers described by size); in
  0.3.0 a huge value produced a huge message, and a word or out-of-range code beyond Python's
  4300-digit printing limit (`from_fxp(10**5000, 8, 5)`, `to_fxp("1e9000", 8, -4000)`) made
  the message itself raise a plain `ValueError`, checked against PyPI 0.3.0.
- Results no longer depend on the caller's `decimal` context; with PyPI 0.3.0 a context with
  `Emax=10` made `FxpSpec(64, 64, False).max_value` raise `decimal.Overflow`, and every bad
  text set the caller's `InvalidOperation` flag.
- `python -m lvfxp`; the command exits 1 quietly when its reader closes the pipe.
- The value math and the byte forms moved into `_layout.py` and `_spec.py` so every source
  file stays under 200 lines; `FxpSpec` is the same frozen dataclass.

## Baseline on 0.3.0 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .` | exit 0 |
| `mypy --strict src tests` | 1 error: `tests/test_limits.py` passes a `memoryview` to `unpack`, typed `bytes | bytearray` |
| `pytest --doctest-modules src` | no doctests at all |

Defects of PyPI 0.3.0 found during this round (each checked against the installed 0.3.0):
a word or out-of-range code beyond Python's 4300-digit printing limit raised a plain
`ValueError` from the message itself; huge values were echoed whole in messages; a caller
context with a small `Emax` made `max_value` raise `decimal.Overflow`; bad text set the
caller's `InvalidOperation` flag; `sys.set_int_max_str_digits(640)` broke
`FxpSpec(64, -4096).resolution`; `pack_array("12")` packed the characters; a `memoryview` of
wide items was measured in items; `typing.get_type_hints` failed on the seven functions and
methods taking `**options`; the CLI exited 120 when its output pipe closed.

## Independent QA lenses (item 19), first round

Each lens was a fresh reviewer that read the certification rules and CERT-1.0.md first,
worked in its own clone, ran things rather than reading, and reported back privately.

| Lens | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- |
| a. API and docs | 9645ac4 to 0782166 | FAIL (4 medium, 7 low, 1 info) | `get_type_hints` failed on the `**options` functions; `delta`/`offset` typed as any number; NumPy integers rejected by `mypy`; README npTDMS claim not in npTDMS's docs; private class name in messages; doctests needing injected globals; wide-integer wording; undocumented decisions (string modes, `clamp`, `iwl` with `delta`, NumPy values). Fixed in 2f7e71c |
| b. Correctness and ground truth | 9645ac4 | PASS (2 low, 2 info) | about 1.85 million oracle cases, 400 CLI runs, 1,300 fixed-point fields of the LabVIEW captures and their 5 type descriptors, NI pages fetched: no disagreement. Stale source URLs, tie and truncate directions presented as NI-stated, negative array count message, signed count not from NI. Fixed in 566701a |
| c. Adversarial and robustness | 0782166 | FAIL (3 medium, 4 low, info) | 1,727,755 fuzz calls, 30,000 in-process and 400 subprocess CLI runs, 24 scaling shapes (linear or capped). Results depended on `sys.set_int_max_str_digits`; batches accepted text and leaked `TypeError`; closed pipes gave exit 120; some usage errors exited 1; argparse echoed huge arguments. Fixed in 60805d6 |
| d. Packaging and real e2e | 514d8ed | FAIL (1 medium, 3 low, info) | 3.10.22, 3.11.17, 3.12.15, 3.13.16, 3.14.8, 3.14.8t, 3.14.6 all green from the wheel; 0.3.0 upgrade matches the CHANGELOG. The e2e module always rebuilt from source and errored with `src` removed; undocumented base class and message suffix; `release.ps1` refused any upload once the name existed. Fixed in a8e90b4 |
