# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-14

The public API is now stable: the sixteen names in `lvfxp.__all__`, their signatures,
defaults and error types follow Semantic Versioning from this release on. The flattened byte
form, the compact form, the array form, the rounding and overflow modes and the `lvfxp`
command keep their 0.3.0 behaviour. See the upgrade notes in
[GUIDE.md](https://github.com/JaviLianes8/lvfxp/blob/main/GUIDE.md#upgrading-from-030).

### Changed

- Integer arguments (`word_length`, `integer_word_length`, `word`) accept any integer type
  through `__index__` (NumPy integers, `int` subclasses), are typed `SupportsIndex` and
  stored as plain `int`; floats, `Decimal`, text and booleans still raise `FxpError`.
- The encode options (`clamp`, `overflow`, `rounding`) are explicit keyword-only parameters
  of every encoding function and method instead of `**options`, so `typing.get_type_hints`
  and `help()` work on all of them. Calls are unchanged; `EncodeOptions` still describes
  them and can still be unpacked into a call.
- `FxpSpec.delta` and `FxpSpec.offset` are typed `Decimal | None` and `Decimal`, which is
  what they always held; the constructor still takes any number.
- Messages for wide integers read `a code of 136 bits` and `a word of 16610 bits`.
- Byte arguments accept any bytes-like buffer and read its raw bytes: a `memoryview` of any
  format (an `array("H")`, for example) counts its bytes, not its items. The type hints now
  say `bytes | bytearray | memoryview`, matching what 0.3.0 already accepted at run time.
- Error messages quote at most 40 characters of a value, and describe integers wider than
  64 bits by their size, so huge input can no longer produce a huge message. A word or an
  out-of-range code beyond Python's 4300-digit printing limit made 0.3.0 raise a plain
  `ValueError` from the message itself; it is now `FxpError` or `FxpOverflowError`.
- Results no longer depend on the caller's `decimal` context: a small `Emax` made
  `min_value`, `max_value` and `decode` raise `decimal.Overflow` for large values, disabled
  traps turned "not a number" into "must be finite", and bad text set the caller's
  `InvalidOperation` flag.
- An integer value wider than about 34000 bits is refused at once with `FxpError` instead of
  being converted first.
- The `lvfxp` command exits 1 quietly when its reader closes the pipe, and cuts error
  messages at 300 characters.

- The value math moved into a private base class; tracebacks and messages still name
  `FxpSpec`.
- The project URL `Repository` is now `Source`, and the sdist ships the tests and the
  LabVIEW captures.

### Added

- `python -m lvfxp` runs the command line tool.
- Every public name and method carries a runnable example; GUIDE.md documents layouts,
  byte forms, rounding, errors and the command line.
- Python 3.10 to 3.14 classifiers and `Development Status :: 5 - Production/Stable`.
- A LabVIEW 2026 capture of all 256 `Integer to Fixed-Point Cast` results of the shipped
  `Fixed-Point Cast.vi` example, decoded and re-packed byte for byte by the tests.

## [0.3.0] - 2026-10-12

The first release published to PyPI.

This release corrects the flattened byte layout. 0.2.0 described its `ceil(wl / 8)`-byte
output as LabVIEW's flattened form; it is not, and bytes from 0.2.0 `pack` are not
LabVIEW data.

### Changed

- `pack`, `unpack`, `pack_fxp` and `unpack_fxp` now use LabVIEW's flattened form: 8
  big-endian bytes, the word in the low bits, sign extended when signed and zero extended
  when unsigned, as NI documents and as a real LabVIEW 2026 capture confirms. `unpack`
  rejects high bits that are not the word's extension, and 9-byte input (a value with an
  overflow status, whose layout NI does not document) with an explanatory error.
- `FxpSpec.byte_length` is now always 8.
- `FxpSpec` accepts word lengths from 1 to 64 only, LabVIEW's limits.
- `FxpSpec` accepts integer word lengths from -4096 to 4096 (a library bound), and
  numbers with a decimal exponent beyond +/-10000 raise `FxpError`, so no input can make
  exact arithmetic run without bound.
- The CLI prints and reads the 8-byte form; `--rounding` now takes LabVIEW's names
  (`half-even`, `half-up`, `truncate`), and `decode` prints exact plain notation.

### Added

- The previous dense form, under an explicit non-LabVIEW name: `pack_compact`,
  `unpack_compact`, `compact_byte_length`, `pack_fxp_compact` and `unpack_fxp_compact`.
- `FxpSpec.pack_array` and `FxpSpec.unpack_array` for flattened 1-D arrays.
- LabVIEW rounding constants `LV_ROUND_HALF_EVEN`, `LV_ROUND_HALF_UP` (ties toward positive
  infinity) and `LV_TRUNCATE`, plus `overflow="raise" | "saturate" | "wrap"`.
- `FLATTENED_SIZE`, `MAX_WORD_LENGTH`, `MAX_INTEGER_WORD_LENGTH` and the `EncodeOptions` typed keyword options.
- CLI: `info` command, `--compact`, `--overflow`.

### Fixed

- A non-bool `clamp`, a non-string `rounding` or `overflow`, and non-bytes data now raise
  `FxpError` instead of being accepted or leaking `TypeError`.
- Resolutions finer than about `2 ** -40` were rounded to 28 significant digits; they are
  now exact.
- Rounding is exact over rationals, so an explicit `delta` can no longer double-round near
  a tie.
- Malformed or non-finite values raise `FxpError` instead of `decimal.InvalidOperation`,
  which also made the CLI exit with a traceback.

## [0.2.0]

Not published to PyPI.

- Flattened byte codec: `pack_fxp` and `unpack_fxp`, plus `FxpSpec.pack`, `FxpSpec.unpack`
  and `FxpSpec.byte_length`, writing the word in `ceil(word_length / 8)` big-endian bytes.
  Corrected in 0.3.0: this is not LabVIEW's flattened form.
- `FxpSpec.encode_many` and `FxpSpec.decode_many` apply one layout to many values.
- New `lvfxp` command line tool with `encode` and `decode` subcommands and `--version`.

## [0.1.0]

Not published to PyPI.

- First release: encode and decode LabVIEW fixed-point (FXP) numbers in pure Python.
- `to_fxp` and `from_fxp` convert between a real value and the two's-complement word for a
  `<signed, word length, integer word length>` layout, exact via `Decimal`.
- `FxpSpec` describes a layout, exposes its resolution and representable range, and
  supports general fixed-point with an explicit delta and offset.
- Fills the gap left by autolv and npTDMS, which do not decode the FXP type.
