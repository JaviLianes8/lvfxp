# lvfxp

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Encode and decode LabVIEW fixed-point (FXP) numbers and their flattened bytes, exactly, in
pure Python, with no dependencies. Python 3.10 or newer.

The full reference is the [guide](https://github.com/JaviLianes8/lvfxp/blob/main/GUIDE.md);
every release is described in the
[changelog](https://github.com/JaviLianes8/lvfxp/blob/main/CHANGELOG.md).

## Install

```
pip install lvfxp
```

## What is a LabVIEW fixed-point number

A LabVIEW fixed-point number stores a real value as an integer word plus a layout that
says how to read it: `<signed, word length, integer word length>`. The word holds
`word length` bits (1 to 64, two's complement when signed), and the integer word length
fixes where the binary point sits. The real value is the word read as an integer times the
resolution `2 ** (integer word length - word length)`. The integer word length may exceed
the word length or go negative; lvfxp accepts -4096 to 4096 (its own bound, not
LabVIEW's, which keeps exact values a sane size). A general fixed-point layout may instead carry an explicit
delta (resolution) and offset, giving `offset + word * delta`.

## Usage

```python
from decimal import Decimal

from lvfxp import FxpSpec, from_fxp, to_fxp

# Signed layout with word length 8 and integer word length 5: resolution 0.125.
word = to_fxp(Decimal("15.875"), 8, 5)  # 127 (0x7F)
value = from_fxp(word, 8, 5)  # Decimal("15.875")

# A spec exposes the resolution and the representable range.
spec = FxpSpec(word_length=8, integer_word_length=5, signed=True)
spec.resolution  # Decimal("0.125")
spec.min_value, spec.max_value  # (Decimal("-16.000"), Decimal("15.875"))

# General fixed-point with an explicit delta and offset.
FxpSpec(8, 8, signed=False, delta=Decimal("0.1"), offset=Decimal("1")).decode(5)  # Decimal("1.5")
```

Decoding returns a `Decimal` that is exact at every width, including the `2 ** -64`
resolution of a `<64, 0>` word. Floats are read through their shortest repr, so `0.1`
means `Decimal("0.1")`. Bad input (text that is not a number, NaN, infinity, a decimal exponent
beyond +/-10000, a word that does not fit, data that is not bytes) raises `FxpError`, a
`ValueError`. Results never depend on the caller's `decimal` context.

## Rounding and overflow

Encoding rounds exactly, over rationals, so no mode can double-round near a tie. LabVIEW's
three rounding modes are provided as constants:

| Constant | LabVIEW mode | Ties |
| --- | --- | --- |
| `LV_ROUND_HALF_EVEN` (default) | Round-Half-Even | to the even code |
| `LV_ROUND_HALF_UP` | Round-Half-Up (asymmetric) | toward positive infinity |
| `LV_TRUNCATE` | Truncate | always rounds down (drops low bits) |

Any `decimal` rounding mode is accepted too. Note that `decimal.ROUND_HALF_UP` rounds ties
away from zero, which differs from LabVIEW's Round-Half-Up for negative values.

```python
from decimal import Decimal

from lvfxp import LV_ROUND_HALF_UP, to_fxp

to_fxp(Decimal("-0.0625"), 8, 5, rounding=LV_ROUND_HALF_UP)  # 0, the tie goes up
to_fxp(Decimal("16"), 8, 5, overflow="saturate")  # 127, the largest code
to_fxp(Decimal("16"), 8, 5, overflow="wrap")  # 128 (0x80), the low 8 bits
```

`overflow` is `"raise"` (the default, `FxpOverflowError`), `"saturate"` or `"wrap"`;
`clamp=True` is shorthand for `"saturate"`. LabVIEW's To Fixed-Point saturates by default;
lvfxp raises by default so an out-of-range value never passes silently.

## Flattened bytes

LabVIEW holds every fixed-point number in a 64-bit format and sign extends it to 64 bits,
and it flattens numbers big-endian. `pack` and `unpack` read and write that form: 8 bytes,
the word in the low bits, sign extended when signed and zero extended when unsigned.

```python
from decimal import Decimal

from lvfxp import FxpSpec, pack_fxp, unpack_fxp

pack_fxp(Decimal("-16"), 8, 5).hex()  # "ffffffffffffff80"
unpack_fxp(bytes.fromhex("00000000000003e5"), 10, 4, signed=False)  # Decimal("15.578125")

spec = FxpSpec(word_length=8, integer_word_length=5)
spec.byte_length  # 8
spec.pack_array([Decimal("1"), Decimal("-1")]).hex()
# "00000002" "0000000000000008" "fffffffffffffff8": a 32-bit count, then the elements
```

`unpack` checks that the high bits are the word's extension, so bytes written for a
different word length or signedness raise instead of decoding to a wrong value.

### What is verified, and what is not

- **Value math: derived and checked.** Word length, integer word length (the number of
  integer bits), signedness and the names of the rounding and overflow modes follow NI's
  documentation; the scaling `2 ** (iwl - wl)` follows from the number of integer bits and
  is not captured from LabVIEW. A contract test
  checks every word of each word length up to 8 bits, at several integer word lengths,
  against independent rational arithmetic.
- **Tie and truncate directions: derived.** NI says Round-Half-Up adds to the least
  significant bit and Truncate removes bits; that ties go toward positive infinity and
  Truncate rounds toward negative infinity follows from two's-complement arithmetic. It is
  not stated by NI and was not captured.
- **8-byte layout: verified.** NI documents the 64-bit, sign-extended format and
  big-endian flattening, and its numeric table gives fixed-point 64 bits of storage on
  disk. Real LabVIEW 2026 captures agree byte for byte: front-panel datalog records
  written by the shipped `Fixed-Point Cast.vi` example store each fixed-point value as 8
  big-endian bytes, signed words sign extended and an unsigned `<+, 10, 4>` word with its
  top bit set zero extended; one capture holds the example's Integer to Fixed-Point Cast
  of every I8 value, 768 flattened words (`tests/fixtures/labview2026`). The output of the Flatten To
  String function itself was not captured; NI Community reports of 8-byte flattened
  fixed-point strings (see Sources) match the same form.
- **1-D arrays: derived, not captured.** `pack_array`/`unpack_array` combine NI's
  documented array rule (a 32-bit count, then the elements) with the verified 8-byte
  element.
- **Overflow status: not supported.** NI gives 72 bits when a fixed-point value includes an
  overflow status, but does not document where the status byte sits or how it is encoded,
  and no capture was possible, so lvfxp refuses 9-byte input instead of guessing.

### Compact form (not LabVIEW)

`pack_compact`/`unpack_compact` (and `pack_fxp_compact`/`unpack_fxp_compact`) store the
word in `ceil(word_length / 8)` big-endian bytes. This is a dense form for your own files
or links; LabVIEW does not read or write it. Unpacking it ignores bits above the word.

## Command line

Installing the package adds an `lvfxp` command (`python -m lvfxp` works too).

```
$ lvfxp encode 15.875 --wl 8 --iwl 5
000000000000007f
$ lvfxp encode 16 --wl 8 --iwl 5 --overflow saturate
000000000000007f
$ lvfxp decode ffffffffffffff80 --wl 8 --iwl 5
-16
$ lvfxp decode 7f --wl 8 --iwl 5 --compact
15.875
$ lvfxp decode --word 128 --wl 8 --iwl 5 --unsigned
16
$ lvfxp info --wl 8 --iwl 5
layout: <+/-, 8, 5>
resolution: 0.125
minimum: -16
maximum: 15.875
flattened bytes: 8
compact bytes: 1
```

`encode` prints the flattened hex, the integer word with `--word`, or the compact hex with
`--compact`; it takes `--overflow`, `--clamp` and `--rounding half-even|half-up|truncate`.
`decode` reads flattened hex, compact hex with `--compact`, or an integer with `--word`, and
prints the exact value in plain notation. Every command takes `--wl`, `--iwl`,
`--unsigned`, `--delta` and `--offset`; `lvfxp --help` lists runnable examples. Data errors
print to stderr with exit code 1; usage errors exit 2. Put `--` before a negative value
in scientific notation, as in `lvfxp encode --wl 8 --iwl 5 -- -1e0` (needed before Python
3.14).

## Why

Fixed-point is a core LabVIEW datatype, handled natively by LabVIEW's own flatten and
type-descriptor machinery (there is no separate OpenG FXP package); that machinery runs
inside LabVIEW only. LabVIEW exchanges fixed-point data through TDMS files, flattened
strings and network streams, but the Python tools that read those sources do not decode
the FXP type: [autolv](https://pypi.org/project/autolv/) states fixed-point is not
supported, and [npTDMS](https://pypi.org/project/npTDMS/) has no fixed-point entry in
[its table of TDMS data types](https://github.com/adamreeve/npTDMS/blob/master/nptdms/types.py). General fixed-point maths packages such as `fxpmath` and `fixedpoint` implement
their own arithmetic, not LabVIEW's wire layout. `struct` and `numpy` have no type for an
arbitrary word length with a shifting or negative integer word length. `lvfxp` fills that
gap with a small, zero-dependency, exact codec.

## Sources

- NI, [How LabVIEW Stores Data in Memory](https://www.ni.com/docs/en-US/bundle/labview/page/how-labview-stores-data-in-memory.html):
  fixed-point numbers have a 64-bit format, signed and unsigned, sign extended to 64 bits.
- NI, [Flattened Data](https://www.ni.com/docs/en-US/bundle/labview/page/flattened-data.html):
  flattened numeric data is big-endian; arrays start with 32-bit dimension sizes.
- NI, [Numeric Data Types Table](https://www.ni.com/docs/en-US/bundle/labview/page/numeric-data-types-table.html):
  fixed-point takes 64 bits of storage on disk, or 72 with an overflow status.
- NI, [Configuring Fixed-Point Numbers](https://www.ni.com/docs/en-US/bundle/labview/page/configuring-fixed-point-numbers.html):
  the integer word length is the number of integer bits used for the value.
- NI, [Fixed-Point Numbers](https://www.ni.com/docs/en-US/bundle/labview/page/fixed-point-numbers.html):
  word length between 1 and 64 bits, signed or unsigned.
- NI, [LabVIEW FPGA fixed-point data type](https://www.ni.com/docs/en-US/bundle/labview-fpga-module/page/using-the-fixed-point-data-type-fpga-module.html):
  Truncate, Round-Half-Up (asymmetric) and Round-Half-Even (the fixed-point default);
  Saturate and Wrap.
- NI, [To Fixed-Point](https://www.ni.com/docs/en-US/bundle/labview-api-ref/page/functions/to-fixed-point.html):
  saturates by default on overflow.
- NI Community, [Flatten FXP to string](https://forums.ni.com/t5/LabVIEW/Flatten-FXP-to-string/m-p/1514224)
  and [Flatten to String adds extra bytes to fixed point numbers](https://forums.ni.com/t5/LabVIEW/Flatten-to-String-vi-adds-extra-bytes-to-fixed-point-numbers/td-p/2923098):
  users report 8-byte flattened output for 24-bit and 32-bit fixed-point values.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/lvfxp/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
