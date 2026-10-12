# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0]

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

- Flattened byte codec: `pack_fxp` and `unpack_fxp`, plus `FxpSpec.pack`, `FxpSpec.unpack`
  and `FxpSpec.byte_length`, writing the word in `ceil(word_length / 8)` big-endian bytes.
  Corrected in 0.3.0: this is not LabVIEW's flattened form.
- `FxpSpec.encode_many` and `FxpSpec.decode_many` apply one layout to many values.
- New `lvfxp` command line tool with `encode` and `decode` subcommands and `--version`.

## [0.1.0]

- First release: encode and decode LabVIEW fixed-point (FXP) numbers in pure Python.
- `to_fxp` and `from_fxp` convert between a real value and the two's-complement word for a
  `<signed, word length, integer word length>` layout, exact via `Decimal`.
- `FxpSpec` describes a layout, exposes its resolution and representable range, and
  supports general fixed-point with an explicit delta and offset.
- Fills the gap left by autolv and npTDMS, which do not decode the FXP type.
