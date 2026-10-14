# lvfxp 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0, e654fd6)
- [x] Real LabVIEW 2026 capture: every I8 value through `Fixed-Point Cast.vi` (item 7)
- [ ] Baseline gates run on 0.3.0
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18): contracts and seeded oracle written; mutation round running
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19): lenses a to e started at 9645ac4
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
  0.3.0 a huge value produced a huge message, and an out-of-range code wider than about 14000
  bits made the message itself raise a plain `ValueError`.
- Results no longer depend on the caller's `decimal` context.
- `python -m lvfxp`; the command exits 1 quietly when its reader closes the pipe.
- The value math and the byte forms moved into `_layout.py` and `_spec.py` so every source
  file stays under 200 lines; `FxpSpec` is the same frozen dataclass.
