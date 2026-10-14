# lvfxp 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0, e654fd6)
- [x] Real LabVIEW 2026 capture: every I8 value through `Fixed-Point Cast.vi` (item 7)
- [x] Baseline gates run on 0.3.0
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19): first round done (b PASS; a, c, d, e FAIL, fixed); re-verification under way
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
| e. Contract strength | 0782166 | FAIL until its contracts were added | blind round designed from the source: 94 mutations, 75 killed, 5 proven equivalent (with a 5.08 million output differential check), 14 survivors; the 14 contracts it proposed were added in 3f53b93 (`tests/test_contract_strength.py`; the array-count one is covered by `tests/test_contract_edges.py` since a negative count got its own message). It also noted argparse echoing huge numbers, fixed in 60805d6 |

## Author mutation round (item 18)

Each mutation was applied alone to a clean clone of the branch, `__pycache__` purged, no
bytecode written, the suite run with `-x` and a per-mutant timeout, and the clone restored; the
full suite (wheel end to end included) was green before and after. The first run (1e25323, 52
mutations) left 11 survivors; contracts were added in 514d8ed and later commits. The table is
the final run at a8e90b4 (57 mutations, the mutated text updated where the source had moved),
with M39 and M42 re-applied at 8ecb78f: 54 killed (8 of them only after a new contract),
3 equivalent.

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| M01 | flatten little-endian | `_flat.py` | killed | `tests/test_bytes.py::test_pack_writes_labviews_flattened_form[000000000000007f-8-5-True-value0]` |
| M02 | unflatten little-endian | `_flat.py` | killed | `tests/test_bytes.py::test_unpack_reads_labviews_flattened_form[000000000000007f-8-5-True-value0]` |
| M03 | no sign extension | `_flat.py` | killed | `tests/test_bytes.py::test_pack_writes_labviews_flattened_form[ffffffffffffff80-8-5-True-value1]` |
| M04 | unsigned read as signed | `_flat.py` | killed | `tests/test_bytes.py::test_unpack_reads_labviews_flattened_form[ffffffffffffffff-64-64-False-value11]` |
| M05 | extension check dropped | `_flat.py` | killed | `tests/test_bytes.py::test_unpack_rejects_high_bits_that_are_not_the_extension` |
| M06 | compact size off by one | `_flat.py` | killed | `tests/test_bytes.py::test_compact_form_is_ceil_word_length_over_eight_bytes` |
| M07 | compact high bits kept | `_flat.py` | killed | `tests/test_bytes.py::test_compact_unpack_ignores_bits_above_the_word` |
| M08 | 9-byte hint wrong size | `_flat.py` | killed | `tests/test_bytes.py::test_unpack_rejects_the_wrong_size_and_explains_nine_bytes` |
| M09 | array count little-endian | `_flat.py` | killed | `tests/test_bytes.py::test_array_is_a_count_then_eight_byte_elements` |
| M10 | array trailing bytes accepted | `_flat.py` | survived, then killed | `tests/test_contract_edges.py::test_an_array_with_trailing_bytes_is_refused` |
| M11 | array count unsigned | `_flat.py` | survived, then killed | `tests/test_contract_edges.py::test_the_array_count_is_read_as_a_signed_32_bit_integer` |
| M12 | buffer copied by bytes() | `_flat.py` | killed | `tests/test_hostile.py::test_a_bytes_subclass_cannot_lie_about_itself` |
| M13 | LV half-up away from zero | `_quantize.py` | killed | `tests/test_cli.py::test_every_help_example_prints_what_it_claims[args5-0000000000000000]` |
| M14 | half-even to odd | `_quantize.py` | killed | `tests/test_codec.py::test_half_even_rounding_is_the_default` |
| M15 | tie decided before mode | `_quantize.py` | equivalent | equivalent: the changed comparison sits inside `rest != 1/2`, where `<` and `<=` agree |
| M16 | truncate toward zero | `_quantize.py` | killed | `tests/test_codec.py::test_labview_truncate_rounds_toward_negative_infinity` |
| M17 | ROUND_DOWN floors | `_quantize.py` | killed | `tests/test_oracle.py::test_encode_rounds_and_overflows_like_the_oracle[0]` |
| M18 | saturate swapped | `_quantize.py` | killed | `tests/test_codec.py::test_overflow_saturates_when_requested` |
| M19 | wrap loses sign | `_quantize.py` | equivalent | equivalent: `encode` adds 2**wl to a negative code, so the wrapped word is the same either way |
| M20 | clamp+wrap accepted | `_quantize.py` | killed | `tests/test_codec.py::test_wrap_and_clamp_cannot_be_combined` |
| M21 | clamp type unchecked | `_quantize.py` | killed | `tests/test_limits.py::test_option_types_are_checked` |
| M22 | overflow wrong error type | `_quantize.py` | killed | `tests/test_codec.py::test_overflow_raises_by_default` |
| M23 | exact values rounded | `_quantize.py` | killed | `tests/test_oracle.py::test_encode_rounds_and_overflows_like_the_oracle[0]` |
| M24 | wl 65 accepted | `_layout.py` | killed | `tests/test_cli.py::test_data_errors_go_to_stderr_with_exit_one[args2-between 1 and 64]` |
| M25 | iwl bound off by one | `_layout.py` | killed | `tests/test_hostile.py::test_the_int_string_limit_of_the_caller_changes_nothing` |
| M26 | resolution exponent swapped | `_layout.py` | killed | `tests/test_bytes.py::test_unpack_reads_labviews_flattened_form[000000000000007f-8-5-True-value0]` |
| M27 | zero delta accepted | `_layout.py` | killed | `tests/test_spec.py::test_delta_must_be_positive` |
| M28 | unsigned max halved | `_layout.py` | killed | `tests/test_cli.py::test_info_describes_the_layout` |
| M29 | encode returns signed code | `_layout.py` | killed | `tests/test_bytes.py::test_pack_writes_labviews_flattened_form[ffffffffffffff80-8-5-True-value1]` |
| M30 | unsigned accepts negative word | `_layout.py` | equivalent | equivalent: an unsigned layout has a minimum code of 0, so a negative word still fails the next check |
| M31 | word 2**wl accepted | `_layout.py` | killed | `tests/test_codec.py::test_decode_rejects_a_word_that_is_too_wide` |
| M32 | caller context used | `_layout.py` | killed | `tests/test_cli.py::test_decode_prints_plain_exact_digits` |
| M33 | offset sign in encode | `_layout.py` | killed | `tests/test_oracle.py::test_general_layouts_match_the_oracle[0]` |
| M34 | signed type unchecked | `_layout.py` | killed | `tests/test_spec.py::test_layout_fields_are_type_checked` |
| M35 | float binary expansion | `_numbers.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvfxp._numbers]` |
| M36 | bool accepted as value | `_numbers.py` | killed | `tests/test_spec.py::test_bad_values_raise_fxp_error_not_decimal_errors[True]` |
| M37 | huge adjusted exponent accepted | `_numbers.py` | survived, then killed | `tests/test_contract_edges.py::test_a_long_digit_string_is_refused_for_its_size_not_saturated` |
| M38 | message bound lifted | `_numbers.py` | killed | `tests/test_docs.py::test_guide_examples_run_and_print_what_they_show` |
| M39 | wide ints printed | `_numbers.py` | survived, then killed | new `tests/test_contract_edges.py::test_a_wide_word_length_is_described_by_its_size` (re-applied at 8ecb78f) |
| M40 | bool accepted as an integer field | `_numbers.py` | killed | `tests/test_hostile.py::test_non_integers_are_refused_for_integer_fields[True]` |
| M41 | caller context traps used | `_numbers.py` | killed | `tests/test_hostile.py::test_the_callers_decimal_context_changes_nothing[context2]` |
| M42 | huge int guard lifted | `_numbers.py` | survived, then killed | `tests/test_contract_edges.py::test_a_huge_integer_is_refused_before_any_conversion` (re-applied at 8ecb78f) |
| M43 | data error exit 2 | `_cli.py` | killed | `tests/test_cli.py::test_data_errors_go_to_stderr_with_exit_one[args0-outside]` |
| M44 | CLI half-up mapped wrong | `_cli.py` | survived, then killed | `tests/test_contract_edges.py::test_cli_half_up_sends_positive_ties_up` |
| M45 | CLI default compact | `_cli.py` | killed | `tests/test_cli.py::test_every_help_example_prints_what_it_claims[args0-000000000000007f]` |
| M46 | plain keeps trailing zeros | `_cli.py` | killed | `tests/test_cli.py::test_every_help_example_prints_what_it_claims[args7--16]` |
| M47 | CLI signedness inverted | `_cli.py` | killed | `tests/test_cli.py::test_every_help_example_prints_what_it_claims[args1-fffffffffffffffb]` |
| M48 | CLI message unbounded | `_cli.py` | survived, then killed | `tests/test_contract_edges.py::test_cli_cuts_any_long_error_message` |
| M49 | unpack_fxp ignores signed | `_codec.py` | killed | `tests/test_bytes.py::test_unpack_reads_labviews_flattened_form[00000000000003e5-10-4-False-value5]` |
| M50 | from_fxp args swapped | `_codec.py` | killed | `tests/test_codec.py::test_unsigned_binary_point_example` |
| M51 | byte_length compact | `_spec.py` | killed | `tests/test_bytes.py::test_flattened_size_is_always_eight_bytes` |
| M52 | unpack_array signed | `_spec.py` | survived, then killed | `tests/test_contract_edges.py::test_an_unsigned_array_keeps_words_with_the_top_bit_set` |
| M53 | text accepted as a batch | `_numbers.py` | killed | `tests/test_hostile.py::test_batch_calls_want_an_iterable_of_items[12]` |
| M54 | fine resolution rounded | `_layout.py` | killed | `tests/test_cli.py::test_decode_prints_plain_exact_digits` |
| M55 | usage problem exits 1 | `_cli.py` | killed | `tests/test_cli.py::test_usage_errors_exit_two_with_a_short_message[args1-use --word]` |
| M56 | usage message unbounded | `_cli_io.py` | killed | `tests/test_cli.py::test_usage_errors_exit_two_with_a_short_message[args4-invalid int value]` |
| M57 | count -1 accepted | `_flat.py` | killed | `tests/test_contract_edges.py::test_the_array_count_is_read_as_a_signed_32_bit_integer` |

Equivalent: M15 (the changed comparison is reached only when the remainder is not one half,
where `<` and `<=` agree), M19 (`encode` adds `2**wl` to a negative code, so the word is the
same), M30 (an unsigned layout's minimum code is 0, so a negative word still fails the next
check). In the first run, a check refusing floats, `Decimal`, `Fraction` and text as integer
fields was shown redundant (`operator.index` refuses them) and removed.

## Later QA rounds (item 19)

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| c | 2 (new reviewer) | 4f4a025 | FAIL (1 medium, 3 low, info) | 14,617 seeded API calls, 300 fuzzed and 224 matrix CLI runs, threads under a hostile context and a 640-digit limit, scaling linear to 10^7; all seven earlier findings fixed. New: an object faking `__class__` (a mock with `spec=`) gave a raw `TypeError` from inside lvfxp; 19-digit exponents named "not a number"; exit 120 when a descriptor was closed inside the process; `--help` exited 0 when its output was lost. Fixed in 3be5bee |
| c | 3 (new reviewer) | 48e85a6 | FAIL (1 medium, 2 low, 3 info) | about 300,900 seeded API calls, 4,500 in-process and 90 subprocess CLI runs, a hostile battery with mocks and faked classes, threads; the four earlier findings fixed. New: the exponent grammar added in 3be5bee backtracked quadratically on long non-numbers; the lost-help flag stuck to later in-process calls; a failing stream silenced both descriptors; zero with a 25-digit exponent refused; non-ASCII digits undocumented; resolution recomputed per item in batches. Fixed in 3e6846d |
| e | 2 (new reviewer, blind) | 4f4a025 | PASS with its contracts | 135 mutations designed from the source alone: 104 killed, 5 proven equivalent, 26 survivors; its 21 contracts added in d960865 (`tests/test_contract_strength_two.py`), plus options now checked even for an empty batch (its other finding) and a dead `"-0"` branch of the command's number printer removed |
| c | 4 (new reviewer) | b97ca0e | PASS (1 low, 3 info) | 2,780,000 seeded API calls with in-process CLI runs, 300 subprocess runs over closed and redirected streams, 44 scaling dimensions all linear to 10^7 (capped fields at most 10.5 ms), about 120 hostile objects, threads; all six earlier findings fixed. Notes: a `TypeError` from the caller's `__index__` became `FxpError` although GUIDE says it propagates; option names compared through a `str` subclass's own `__eq__`; a `bytes` subclass's `__buffer__` honoured. All three addressed in 1b71ab1 |
