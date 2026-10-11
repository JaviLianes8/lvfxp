# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

- Flattened byte codec: `pack_fxp` and `unpack_fxp`, plus `FxpSpec.pack`, `FxpSpec.unpack`
  and `FxpSpec.byte_length`, read and write the big-endian two's-complement word LabVIEW
  stores, including non-byte-aligned widths.
- `FxpSpec.encode_many` and `FxpSpec.decode_many` apply one layout to many values.
- New `lvfxp` command line tool with `encode` and `decode` subcommands and `--version`.

## [0.1.0]

- First release: encode and decode LabVIEW fixed-point (FXP) numbers in pure Python.
- `to_fxp` and `from_fxp` convert between a real value and the two's-complement word for a
  `<signed, word length, integer word length>` layout, exact via `Decimal`.
- `FxpSpec` describes a layout, exposes its resolution and representable range, and
  supports general fixed-point with an explicit delta and offset.
- Fills the gap left by autolv and npTDMS, which do not decode the FXP type.
