"""The fixed-point specification: word layout, scaling, and range."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from ._errors import FxpError, FxpOverflowError

Number = int | float | Decimal | str


def _as_decimal(value: Number) -> Decimal:
    """Convert to Decimal without inheriting binary float noise."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def _digits(value: Decimal) -> int:
    parts = value.as_tuple()
    return len(parts.digits) + abs(int(parts.exponent))


@dataclass(frozen=True)
class FxpSpec:
    """A LabVIEW fixed-point layout: ``<signed, word_length, integer_word_length>``.

    The stored word holds ``word_length`` bits, two's complement when ``signed``. The
    real value is ``offset + coded * resolution``, where ``coded`` is the word read as an
    integer and ``resolution`` defaults to ``2 ** (integer_word_length - word_length)``.
    ``integer_word_length`` may exceed ``word_length`` or be negative, exactly as LabVIEW
    allows: only the bits that fit are stored.
    """

    word_length: int
    integer_word_length: int
    signed: bool = True
    delta: Number | None = None
    offset: Number = Decimal(0)

    def __post_init__(self) -> None:
        if self.word_length < 1:
            raise FxpError("word_length must be at least 1")
        object.__setattr__(self, "offset", _as_decimal(self.offset))
        if self.delta is not None:
            resolved = _as_decimal(self.delta)
            if resolved <= 0:
                raise FxpError("delta must be positive")
            object.__setattr__(self, "delta", resolved)

    @property
    def resolution(self) -> Decimal:
        """Value of the least significant bit (the quantization step)."""
        if self.delta is not None:
            return _as_decimal(self.delta)
        exponent = self.integer_word_length - self.word_length
        if exponent >= 0:
            return Decimal(2**exponent)
        step = -exponent
        return Decimal(5**step).scaleb(-step)

    @property
    def _coded_min(self) -> int:
        return -(1 << (self.word_length - 1)) if self.signed else 0

    @property
    def _coded_max(self) -> int:
        if self.signed:
            return (1 << (self.word_length - 1)) - 1
        return (1 << self.word_length) - 1

    @property
    def min_value(self) -> Decimal:
        """Smallest representable real value."""
        return self._scale(self._coded_min)

    @property
    def max_value(self) -> Decimal:
        """Largest representable real value."""
        return self._scale(self._coded_max)

    def _scale(self, coded: int) -> Decimal:
        resolution = self.resolution
        offset = _as_decimal(self.offset)
        with localcontext() as ctx:
            ctx.prec = _digits(Decimal(coded)) + _digits(resolution) + _digits(offset) + 10
            return offset + Decimal(coded) * resolution

    def encode(
        self,
        value: Number,
        *,
        clamp: bool = False,
        rounding: str = ROUND_HALF_EVEN,
    ) -> int:
        """Return the unsigned ``word_length``-bit word for ``value``.

        Out-of-range values raise :class:`FxpOverflowError` unless ``clamp`` saturates
        them to the nearest representable bound. ``rounding`` is any ``decimal`` mode.
        """
        target = _as_decimal(value)
        resolution = self.resolution
        offset = _as_decimal(self.offset)
        with localcontext() as ctx:
            ctx.prec = _digits(target) + _digits(resolution) + _digits(offset) + 10
            quotient = (target - offset) / resolution
            coded = int(quotient.to_integral_value(rounding=rounding))
        coded = self._fit(coded, clamp)
        return coded + (1 << self.word_length) if coded < 0 else coded

    def decode(self, word: int) -> Decimal:
        """Return the real value of an unsigned ``word_length``-bit word.

        A negative ``word`` is accepted as an already-signed value when the layout is
        signed, so decoding round-trips whichever form the caller holds.
        """
        span = 1 << self.word_length
        if word < 0:
            if not self.signed or word < self._coded_min:
                raise FxpError(f"word {word} is out of range for this layout")
            word += span
        if not 0 <= word < span:
            raise FxpError(f"word {word} does not fit {self.word_length} bits")
        coded = word - span if self.signed and word > self._coded_max else word
        return self._scale(coded)

    def _fit(self, coded: int, clamp: bool) -> int:
        low, high = self._coded_min, self._coded_max
        if coded < low or coded > high:
            if not clamp:
                raise FxpOverflowError(f"value needs code {coded}, outside [{low}, {high}]")
            return min(max(coded, low), high)
        return coded
