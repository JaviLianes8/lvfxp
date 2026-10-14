"""A fixed-point layout and its value math: resolution, range, exact encode and decode."""

from __future__ import annotations

import functools
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Context, Decimal
from fractions import Fraction
from typing import SupportsIndex

from ._errors import FxpError
from ._numbers import (
    Number,
    as_decimal,
    as_fraction,
    as_int,
    as_items,
    describe,
    digits,
    power_of_two,
    short,
)
from ._quantize import (
    LV_ROUND_HALF_EVEN,
    EncodeOptions,
    check_options,
    fit,
    round_exact,
)

MAX_WORD_LENGTH = 64
"""LabVIEW fixed-point words hold between 1 and 64 bits."""

MAX_INTEGER_WORD_LENGTH = 4096
"""lvfxp's own bound on ``abs(integer_word_length)``, keeping exact values a sane size."""


@functools.lru_cache(maxsize=256)
def _derive(exponent: int, delta: str | None, offset: str) -> tuple[Decimal, Fraction, Fraction]:
    """Resolution and exact fractions of a layout; text keys keep each Decimal's spelling."""
    step = power_of_two(exponent) if delta is None else Decimal(delta)
    return step, Fraction(step), Fraction(Decimal(offset))


_FIELDS = ("word_length", "integer_word_length", "signed", "delta", "offset")


@dataclass(frozen=True, init=False)
class Layout:
    """Fields and value math of :class:`lvfxp.FxpSpec` (documented there)."""

    word_length: int
    integer_word_length: int
    signed: bool = True
    delta: Decimal | None = None
    offset: Decimal = Decimal(0)

    def __init__(
        self,
        word_length: SupportsIndex,
        integer_word_length: SupportsIndex,
        signed: bool = True,
        delta: Number | None = None,
        offset: Number = 0,
    ) -> None:
        for name, value in zip(
            _FIELDS, (word_length, integer_word_length, signed, delta, offset), strict=True
        ):
            object.__setattr__(self, name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        # Also run by the __init__ of a dataclass subclass, and after unpickling.
        wl = as_int(self.word_length, "word_length")
        if not 1 <= wl <= MAX_WORD_LENGTH:
            raise FxpError(f"word_length must be between 1 and {MAX_WORD_LENGTH}, got {short(wl)}")
        iwl = as_int(self.integer_word_length, "integer_word_length")
        if abs(iwl) > MAX_INTEGER_WORD_LENGTH:
            bound = MAX_INTEGER_WORD_LENGTH
            raise FxpError(f"integer_word_length must be between -{bound} and {bound}")
        if type(self.signed) is not bool:
            raise FxpError("signed must be a bool")
        delta = None if self.delta is None else as_decimal(self.delta, "delta")
        if delta is not None and delta <= 0:
            raise FxpError("delta must be positive")
        offset = as_decimal(self.offset, "offset")
        for name, value in zip(_FIELDS, (wl, iwl, self.signed, delta, offset), strict=True):
            object.__setattr__(self, name, value)
        self._derived()  # prepared now, so every later call finds it ready

    @property
    def resolution(self) -> Decimal:
        """Value of the least significant bit (the quantization step).

        >>> from lvfxp import FxpSpec
        >>> FxpSpec(8, 5).resolution, FxpSpec(8, 8, delta="0.1").resolution
        (Decimal('0.125'), Decimal('0.1'))
        """
        return self._derived()[0]

    @property
    def _coded_min(self) -> int:
        return -(1 << (self.word_length - 1)) if self.signed else 0

    @property
    def _coded_max(self) -> int:
        bits = self.word_length - 1 if self.signed else self.word_length
        return (1 << bits) - 1

    def _derived(self) -> tuple[Decimal, Fraction, Fraction]:
        # Kept out of the instance, so copies, pickles and subclasses carry the fields only.
        delta = None if self.delta is None else str(self.delta)
        return _derive(self.integer_word_length - self.word_length, delta, str(self.offset))

    def _scale(self, coded: int) -> Decimal:
        resolution, offset = self.resolution, self.offset
        # A private context wide enough to be exact, whatever the caller's context says.
        prec = digits(Decimal(coded)) + digits(resolution) + digits(offset) + 10
        context = Context(prec=prec, Emax=999_999, Emin=-999_999)
        return context.add(offset, context.multiply(Decimal(coded), resolution))

    def encode(
        self,
        value: Number,
        *,
        clamp: bool = False,
        overflow: str = "raise",
        rounding: str = LV_ROUND_HALF_EVEN,
    ) -> int:
        """Return the unsigned ``word_length``-bit word for ``value``, rounded exactly.

        ``overflow`` is ``"raise"`` (:class:`FxpOverflowError`), ``"saturate"`` or
        ``"wrap"``; ``clamp=True`` is shorthand for ``"saturate"``. ``rounding`` is a
        ``decimal`` mode or one of ``LV_TRUNCATE``, ``LV_ROUND_HALF_UP``,
        ``LV_ROUND_HALF_EVEN`` (the default, as in LabVIEW).

        >>> from lvfxp import FxpSpec
        >>> spec = FxpSpec(8, 5)
        >>> spec.encode("15.875"), spec.encode(-16), spec.encode(16, overflow="wrap")
        (127, 128, 128)
        """
        mode = check_options(clamp, overflow, rounding)
        _, step, offset = self._derived()
        quotient = (as_fraction(value) - offset) / step
        coded = fit(round_exact(quotient, rounding), self.word_length, self.signed, mode)
        return coded + (1 << self.word_length) if coded < 0 else coded

    def decode(self, word: SupportsIndex) -> Decimal:
        """Return the exact real value of an unsigned ``word_length``-bit word.

        A negative ``word`` is accepted as an already-signed code when the layout is
        signed, so decoding round-trips whichever form the caller holds.

        >>> from lvfxp import FxpSpec
        >>> FxpSpec(8, 5).decode(0x80), FxpSpec(8, 5).decode(-128)
        (Decimal('-16.000'), Decimal('-16.000'))
        """
        span = 1 << self.word_length
        number = as_int(word, "word")
        if number < 0:
            if not self.signed or number < self._coded_min:
                raise FxpError(f"{describe(number, 'word')} is out of range for this layout")
            number += span
        if number >= span:
            raise FxpError(f"{describe(number, 'word')} does not fit {self.word_length} bits")
        return self._scale(number - span if self.signed and number > self._coded_max else number)

    def encode_many(
        self,
        values: Iterable[Number],
        *,
        clamp: bool = False,
        overflow: str = "raise",
        rounding: str = LV_ROUND_HALF_EVEN,
    ) -> list[int]:
        """Encode each value with :meth:`encode` and the same keyword options.

        >>> from lvfxp import FxpSpec
        >>> FxpSpec(8, 5).encode_many([0, "15.875", 99], clamp=True)
        [0, 127, 127]
        """
        options: EncodeOptions = {"clamp": clamp, "overflow": overflow, "rounding": rounding}
        check_options(clamp, overflow, rounding)  # refused even for an empty batch
        return [self.encode(value, **options) for value in as_items(values, "values")]

    def decode_many(self, words: Iterable[SupportsIndex]) -> list[Decimal]:
        """Decode each word with :meth:`decode`, reusing this layout.

        >>> from lvfxp import FxpSpec
        >>> FxpSpec(4, 3).decode_many([0b0101, 0b1011])
        [Decimal('2.5'), Decimal('-2.5')]
        """
        return [self.decode(word) for word in as_items(words, "words")]
