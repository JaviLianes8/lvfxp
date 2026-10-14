# lvfxp guide

This guide covers everything the public API promises. Every `pycon` example and every
`$ lvfxp` transcript below runs as part of the test suite.

## Layouts

A LabVIEW fixed-point layout is `<signed, word length, integer word length>`. `FxpSpec`
holds one:

```pycon
>>> from lvfxp import FxpSpec
>>> spec = FxpSpec(word_length=8, integer_word_length=5)  # signed by default
>>> spec.resolution, spec.min_value, spec.max_value
(Decimal('0.125'), Decimal('-16.000'), Decimal('15.875'))
>>> FxpSpec(8, 5, signed=False).max_value
Decimal('31.875')
```

- `word_length` is 1 to 64 (`MAX_WORD_LENGTH`), LabVIEW's own limits.
- `integer_word_length` may be larger than the word length or negative. lvfxp accepts
  -4096 to 4096 (`MAX_INTEGER_WORD_LENGTH`), its own bound, which keeps exact values a sane
  size.
- Both accept any integer type (`int`, `int` subclasses, NumPy integers) and are stored as
  plain `int`. Floats, `Decimal`, text and booleans raise `FxpError`.
- `signed` must be a `bool`.
- `delta` and `offset` describe a general fixed-point layout whose value is
  `offset + coded * delta`. Both are stored as `Decimal`; `delta` must be positive.
- With a `delta`, the integer word length plays no part in the value; it is still stored and
  compared, so `FxpSpec(8, 8, delta="0.1")` and `FxpSpec(8, 3, delta="0.1")` are not equal.
- Specs are frozen dataclasses: immutable, hashable, equal when their fields are equal.

```pycon
>>> general = FxpSpec(8, 8, signed=False, delta="0.1", offset=1)
>>> general.resolution, general.offset, general.decode(5)
(Decimal('0.1'), Decimal('1'), Decimal('1.5'))
```

## Values

Values may be `int`, `float`, `Decimal` or `str`. A float is read through its shortest
repr, so `0.1` means `Decimal("0.1")`, not the binary double's long expansion. Text is read
as `decimal.Decimal` reads it: surrounding spaces, digit underscores and non-ASCII decimal
digits (`"\u0661\u0662"` is 12) are accepted, and zero is zero whatever its exponent. NaN,
infinities, booleans, other types and decimal exponents beyond +/-10000 raise `FxpError`.
Decoding returns an exact `Decimal`; the `decimal` context of the caller plays no part.

```pycon
>>> from lvfxp import from_fxp, to_fxp
>>> to_fxp(0.1, 16, 1), to_fxp("15.875", 8, 5)
(3277, 127)
>>> from_fxp(1, 64, 0, signed=False)
Decimal('5.42101086242752217003726400434970855712890625E-20')
```

`encode` returns the unsigned word (`0` to `2 ** word_length - 1`). `decode` takes that
word, or, for a signed layout, the already-signed code:

```pycon
>>> spec = FxpSpec(4, 3)
>>> spec.encode("-2.5"), spec.decode(0b1011), spec.decode(-5)
(11, Decimal('-2.5'), Decimal('-2.5'))
```

Values are `int`, `float`, `Decimal` or `str` (subclasses included): `numpy.float64` is a
`float` and is accepted, while `numpy.float32` and NumPy integers are not (convert them with
`float()` or `int()`). Words and layout fields take any integer type.

`encode_many` and `decode_many` apply one layout to many values; `to_fxp` and `from_fxp`
are one-call shortcuts for the common `<signed, wl, iwl>` layout.

## Rounding and overflow

Encoding divides exactly over rationals and rounds once. The default is LabVIEW's
Round-Half-Even. `LV_ROUND_HALF_UP` sends ties toward positive infinity;
`decimal.ROUND_HALF_UP` sends them away from zero. `LV_TRUNCATE` drops low bits, which
rounds toward negative infinity. NI describes Round-Half-Up as adding to the least
significant bit and Truncate as removing bits; both directions follow from two's-complement
arithmetic, and neither was captured from LabVIEW. Any other `decimal` rounding mode is accepted too.

```pycon
>>> from lvfxp import LV_ROUND_HALF_UP, LV_TRUNCATE
>>> to_fxp("-0.0625", 8, 5, rounding=LV_ROUND_HALF_UP)
0
>>> to_fxp("-0.1", 8, 5, rounding=LV_TRUNCATE)
255
```

`overflow="raise"` (the default) raises `FxpOverflowError`; `"saturate"` keeps the nearest
end of the range; `"wrap"` keeps the low bits. `clamp=True` means `"saturate"` and cannot
be combined with `"wrap"`; it is a permanent shorthand. `rounding` and `overflow` are plain
strings in the type hints and are checked at run time (`FxpError` for an unknown name); the
rounding constants are strings too, so they can be stored and passed around freely. LabVIEW's To Fixed-Point saturates by default; lvfxp raises by
default so an out-of-range value never passes silently.

```pycon
>>> to_fxp(16, 8, 5, overflow="saturate"), to_fxp(16, 8, 5, overflow="wrap")
(127, 128)
```

## Byte forms

`pack` and `unpack` use LabVIEW's flattened form: 8 big-endian bytes, the word in the low
bits, sign extended when signed and zero extended when unsigned. `unpack` refuses high bits
that are not the word's extension, so bytes written for another layout raise instead of
decoding to a wrong value.

```pycon
>>> from lvfxp import pack_fxp, unpack_fxp
>>> pack_fxp(-27, 6, 6).hex()
'ffffffffffffffe5'
>>> unpack_fxp(bytes.fromhex("00000000000003e5"), 10, 4, signed=False)
Decimal('15.578125')
```

`pack_array` and `unpack_array` write and read a flattened 1-D array: a big-endian
32-bit count, then the 8-byte elements; the length must match the count exactly. NI calls the
count a 32-bit integer; lvfxp reads it as signed and refuses a negative count.
`pack_compact` and `unpack_compact` store the word in `ceil(word_length / 8)` bytes, a dense
form of lvfxp's own that LabVIEW does not read or write; unpacking it ignores bits above the
word. Every byte argument may be `bytes`, `bytearray` or any `memoryview`, read as its raw
bytes.

```pycon
>>> spec = FxpSpec(8, 5)
>>> spec.pack_array([1, -1]).hex()
'000000020000000000000008fffffffffffffff8'
>>> spec.pack_compact(-16), spec.unpack_compact(b"\x80")
(b'\x80', Decimal('-16.000'))
```

A value with an overflow status (72 bits in LabVIEW) is not supported: NI does not document
where the status sits, so 9-byte input raises `FxpError` with an explanation.

## Errors

| Exception | Raised when |
| --- | --- |
| `FxpOverflowError` | a value is outside the layout's range and `overflow` is `"raise"` |
| `FxpError` | every other refusal: bad layout fields, bad values or options, a word that does not fit, bytes of the wrong size, type or extension |

`FxpOverflowError` is an `FxpError`, which is a `ValueError`, so `except ValueError` catches
both. An exception raised by the caller's own object (an `__index__` that fails, say)
propagates unchanged. Messages quote at most 40 characters of a value and describe integers wider than
64 bits by their size, so hostile input cannot produce a huge message.

```pycon
>>> from lvfxp import FxpError
>>> try:
...     to_fxp("x" * 1000, 8, 5)
... except FxpError as error:
...     print(error)
value is not a number: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx... (1002 characters)
```

## Command line

Installing the package adds the `lvfxp` command; `python -m lvfxp` runs the same tool.

```
$ lvfxp encode -2.5 --wl 4 --iwl 3 --word
11
$ lvfxp encode 15.875 --wl 8 --iwl 5 --compact
7f
$ lvfxp decode 00000000000003e5 --wl 10 --iwl 4 --unsigned
15.578125
$ lvfxp info --wl 8 --iwl 8 --unsigned --delta 0.1 --offset 1
layout: <+, 8> with an explicit delta
offset: 1
resolution: 0.1
minimum: 1
maximum: 26.5
flattened bytes: 8
compact bytes: 1
```

Data errors print `lvfxp: <message>` to stderr and exit 1; usage errors (including `decode`
without hex or `--word`, or with both, and `--clamp` with `--overflow wrap`) exit 2. When the
reader of the output goes away (as with `| head -c 0`), the command exits 1 without a
traceback, `--help` and `--version` included. An integer option longer than Python's
integer-string limit (4300 digits) is refused by the option parser, so it is a usage error.

## What is verified

- Value math and the rounding and overflow mode names follow NI's documentation (the tie
  and truncate directions are derived, see above); the contract tests check
  every word of each word length up to 8 bits, at several integer word lengths, against
  independent rational arithmetic.
- The 8-byte form is checked against front-panel datalog files LabVIEW 2026 wrote on the
  author's PC (`tests/fixtures/labview2026`), including all 256 results of the shipped
  `Fixed-Point Cast.vi` example's Integer to Fixed-Point Cast for every I8 value.
- The array form combines NI's documented array rule with the verified 8-byte element; it
  was not captured.
- LabVIEW's rounding and overflow modes, and the overflow-status form, could not be
  captured with chosen values: LabVIEW's ActiveX server neither sets nor reads fixed-point
  controls.

## Upgrading from 0.3.0

Calls give the same result as in 0.3.0 except in these cases:

- Batches (`encode_many`, `decode_many`, `pack_array`) refuse text, bytes-like objects and
  non-iterables (0.3.0 encoded the characters of `"12"`), and check their options even when
  empty.
- A float subclass such as `numpy.float64` is read through its shortest repr; 0.3.0 raised
  `decimal.InvalidOperation` for `numpy.float64(1.5)`. `numpy.float32` is not a `float` and
  still needs `float()`.
- A `FxpSpec` pickled by 0.3.0 loads and works; 1.0.0 pickles hold only the five fields.
- NumPy integers and other `__index__` types are now accepted where an `int` is expected.
- A `memoryview` whose items are wider than a byte is now read as its raw bytes; 0.3.0
  counted its items and refused or misread it.
- Error message texts changed (long values are cut, wide integers described, some messages
  name the value they refuse). Code that matched on a whole message may need updating; the
  exception types are unchanged, except where 0.3.0 leaked a plain `ValueError` or
  `TypeError` (see the changelog).
- `lvfxp decode` without hex or `--word`, or with both, and `--clamp --overflow wrap` now exit
  2 (usage) instead of 1.
- The caller's `decimal` context no longer changes results.
