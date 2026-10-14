"""A fixed-point layout and its value math: resolution, range, exact encode and decode."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Context, Decimal
from fractions import Fraction
from typing import SupportsIndex, TypedDict

from ._errors import FxpError
from ._numbers import Number, as_decimal, as_fraction, as_int, as_items, describe, digits, short
from ._quantize import LV_ROUND_HALF_EVEN, check_rounding, fit, overflow_mode, round_exact

MAX_WORD_LENGTH = 64
"""LabVIEW fixed-point words hold between 1 and 64 bits."""

MAX_INTEGER_WORD_LENGTH = 4096
"""lvfxp's own bound on ``abs(integer_word_length)``, keeping exact values a sane size."""


class EncodeOptions(TypedDict, total=False):
    """Keyword options shared by every encoding method (see :meth:`FxpSpec.encode`).

    >>> from lvfxp import FxpSpec
    >>> options: EncodeOptions = {"overflow": "saturate"}
    >>> FxpSpec(8, 5).encode(99, **options)
    127
    """

    clamp: bool
    overflow: str
    rounding: str


@dataclass(frozen=True, init=False)
class Layout:
    """Fields and value math of :class:`lvfxp.FxpSpec` (documented there)."""

    word_length: int
    integer_word_length: int
    signed: bool
    delta: Decimal | None
    offset: Decimal

    def __init__(
        self,
        word_length: SupportsIndex,
        integer_word_length: SupportsIndex,
        signed: bool = True,
        delta: Number | None = None,
        offset: Number = 0,
    ) -> None:
        wl = as_int(word_length, "word_length")
        if not 1 <= wl <= MAX_WORD_LENGTH:
            raise FxpError(f"word_length must be between 1 and {MAX_WORD_LENGTH}, got {short(wl)}")
        iwl = as_int(integer_word_length, "integer_word_length")
        if abs(iwl) > MAX_INTEGER_WORD_LENGTH:
            bound = MAX_INTEGER_WORD_LENGTH
            raise FxpError(f"integer_word_length must be between -{bound} and {bound}")
        if not isinstance(signed, bool):
            raise FxpError("signed must be a bool")
        resolved = None if delta is None else as_decimal(delta, "delta")
        if resolved is not None and resolved <= 0:
            raise FxpError("delta must be positive")
        for name, value in (
            ("word_length", wl),
            ("integer_word_length", iwl),
            ("signed", signed),
            ("delta", resolved),
            ("offset", as_decimal(offset, "offset")),
        ):
            object.__setattr__(self, name, value)

    @property
    def resolution(self) -> Decimal:
        """Value of the least significant bit (the quantization step).

        >>> from lvfxp import FxpSpec
        >>> FxpSpec(8, 5).resolution, FxpSpec(8, 8, delta="0.1").resolution
        (Decimal('0.125'), Decimal('0.1'))
        """
        if self.delta is not None:
            return as_decimal(self.delta)
        exponent = self.integer_word_length - self.word_length
        if exponent >= 0:
            return Decimal(2**exponent)
        # 2**e == 5**-e * 10**e, exact in a private context and without int-to-str conversion.
        context = Context(prec=1 - exponent, Emax=999_999, Emin=-999_999)
        return context.scaleb(Decimal(5**-exponent), Decimal(exponent))

    @property
    def _coded_min(self) -> int:
        return -(1 << (self.word_length - 1)) if self.signed else 0

    @property
    def _coded_max(self) -> int:
        bits = self.word_length - 1 if self.signed else self.word_length
        return (1 << bits) - 1

    @property
    def min_value(self) -> Decimal:
        """Smallest representable real value.

        >>> from lvfxp import FxpSpec
        >>> FxpSpec(8, 5).min_value, FxpSpec(8, 5, signed=False).min_value
        (Decimal('-16.000'), Decimal('0.000'))
        """
        return self._scale(self._coded_min)

    @property
    def max_value(self) -> Decimal:
        """Largest representable real value.

        >>> from lvfxp import FxpSpec
        >>> FxpSpec(8, 5).max_value
        Decimal('15.875')
        """
        return self._scale(self._coded_max)

    def _scale(self, coded: int) -> Decimal:
        resolution, offset = self.resolution, as_decimal(self.offset)
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
        mode = overflow_mode(clamp, overflow)
        check_rounding(rounding)
        step = Fraction(self.resolution)
        quotient = (as_fraction(value) - Fraction(as_decimal(self.offset))) / step
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
        return [self.encode(value, **options) for value in as_items(values, "values")]

    def decode_many(self, words: Iterable[SupportsIndex]) -> list[Decimal]:
        """Decode each word with :meth:`decode`, reusing this layout.

        >>> from lvfxp import FxpSpec
        >>> FxpSpec(4, 3).decode_many([0b0101, 0b1011])
        [Decimal('2.5'), Decimal('-2.5')]
        """
        return [self.decode(word) for word in as_items(words, "words")]
