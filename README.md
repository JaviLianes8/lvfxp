# lvfxp

Encode and decode LabVIEW fixed-point (FXP) numbers in pure Python

## Install

```
pip install lvfxp
```

## What is a LabVIEW fixed-point number

A LabVIEW fixed-point (FXP) number stores a real value as a plain integer word plus a
layout that says how to read it: `<signed, word length, integer word length>`. The word
holds `word length` bits (two's complement when signed), and the integer word length
fixes where the binary point sits. The real value is the word read as an integer,
multiplied by the resolution `2 ** (integer word length - word length)`. The integer word
length may exceed the word length or go negative, so the same bits can describe very large
or very small numbers; LabVIEW keeps only the bits that fit. A general FXP may also carry
an explicit delta (resolution) and offset, giving `offset + word * delta`.

## Usage

```python
from decimal import Decimal

from lvfxp import FxpSpec, from_fxp, to_fxp

# Signed layout with word length 8 and integer word length 5: resolution 0.125.
word = to_fxp(Decimal("15.875"), 8, 5)   # 127 (0x7F)
value = from_fxp(word, 8, 5)             # Decimal("15.875")

# Negative values round-trip through two's complement.
from_fxp(to_fxp(Decimal("-2.5"), 4, 3), 4, 3)  # Decimal("-2.5")

# A spec exposes the resolution and the representable range.
spec = FxpSpec(word_length=8, integer_word_length=5, signed=True)
spec.resolution   # Decimal("0.125")
spec.min_value    # Decimal("-16")
spec.max_value    # Decimal("15.875")

# Out-of-range values raise by default, or saturate when you ask them to.
to_fxp(Decimal("16"), 8, 5, clamp=True)  # 127

# General fixed-point with an explicit delta and offset.
FxpSpec(8, 8, signed=False, delta=Decimal("0.1"), offset=Decimal("1")).decode(5)  # Decimal("1.5")
```

Decoding returns a `Decimal`, so results stay exact even at tiny resolutions such as
`2 ** -64`, where a binary float would lose precision. Encoding uses round-half-to-even by
default (LabVIEW's default coercion), and any `decimal` rounding mode can be passed.

## Why

LabVIEW exchanges fixed-point data through TDMS files, flattened strings and network
streams, but the Python tools that read those sources do not decode the FXP type:
[autolv](https://pypi.org/project/autolv/) states fixed-point is not supported, and
[npTDMS](https://pypi.org/project/npTDMS/) lists it among its unsupported types. General
fixed-point maths packages such as `fxpmath` and `fixedpoint` implement their own
arithmetic, not LabVIEW's wire layout, so they cannot read a word that LabVIEW wrote.
`struct` and `numpy` have no type that expresses an arbitrary word length with a shifting
or negative integer word length. `lvfxp` fills that gap with a small, zero-dependency,
exact codec for the documented encoding.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
