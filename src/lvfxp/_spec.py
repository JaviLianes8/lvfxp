"""The fixed-point specification: word layout, scaling, range, and byte forms."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import TYPE_CHECKING, TypedDict

from . import _flat
from ._errors import FxpError
from ._numbers import Number, as_decimal, as_fraction, as_int, digits
from ._quantize import LV_ROUND_HALF_EVEN, check_rounding, fit, overflow_mode, round_exact

if TYPE_CHECKING:
    from typing_extensions import Unpack

MAX_WORD_LENGTH = 64
"""LabVIEW fixed-point words hold between 1 and 64 bits."""

MAX_INTEGER_WORD_LENGTH = 4096
"""lvfxp's own bound on ``abs(integer_word_length)``, keeping exact values a sane size."""


class EncodeOptions(TypedDict, total=False):
    """Keyword options shared by every encoding method (see :meth:`FxpSpec.encode`)."""

    clamp: bool
    overflow: str
    rounding: str


@dataclass(frozen=True)
class FxpSpec:
    """A LabVIEW fixed-point layout: ``<signed, word_length, integer_word_length>``.

    The word holds ``word_length`` bits (1 to 64), two's complement when ``signed``. Its
    real value is ``offset + coded * resolution``, where ``coded`` is the word read as an
    integer and ``resolution`` defaults to ``2 ** (integer_word_length - word_length)``.
    ``integer_word_length`` may exceed ``word_length`` or be negative.
    """

    word_length: int
    integer_word_length: int
    signed: bool = True
    delta: Number | None = None
    offset: Number = Decimal(0)

    def __post_init__(self) -> None:
        if not 1 <= as_int(self.word_length, "word_length") <= MAX_WORD_LENGTH:
            raise FxpError(f"word_length must be between 1 and {MAX_WORD_LENGTH}")
        iwl = as_int(self.integer_word_length, "integer_word_length")
        if abs(iwl) > MAX_INTEGER_WORD_LENGTH:
            bound = MAX_INTEGER_WORD_LENGTH
            raise FxpError(f"integer_word_length must be between -{bound} and {bound}")
        if not isinstance(self.signed, bool):
            raise FxpError("signed must be a bool")
        object.__setattr__(self, "offset", as_decimal(self.offset, "offset"))
        if self.delta is not None:
            resolved = as_decimal(self.delta, "delta")
            if resolved <= 0:
                raise FxpError("delta must be positive")
            object.__setattr__(self, "delta", resolved)

    @property
    def resolution(self) -> Decimal:
        """Value of the least significant bit (the quantization step)."""
        if self.delta is not None:
            return as_decimal(self.delta)
        exponent = self.integer_word_length - self.word_length
        if exponent >= 0:
            return Decimal(2**exponent)
        return Decimal(f"{5**-exponent}E{exponent}")  # exact: scaleb would round

    @property
    def _coded_min(self) -> int:
        return -(1 << (self.word_length - 1)) if self.signed else 0

    @property
    def _coded_max(self) -> int:
        bits = self.word_length - 1 if self.signed else self.word_length
        return (1 << bits) - 1

    @property
    def min_value(self) -> Decimal:
        """Smallest representable real value."""
        return self._scale(self._coded_min)

    @property
    def max_value(self) -> Decimal:
        """Largest representable real value."""
        return self._scale(self._coded_max)

    def _scale(self, coded: int) -> Decimal:
        resolution, offset = self.resolution, as_decimal(self.offset)
        with localcontext() as ctx:
            ctx.prec = digits(Decimal(coded)) + digits(resolution) + digits(offset) + 10
            return offset + Decimal(coded) * resolution

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
        """
        mode = overflow_mode(clamp, overflow)
        check_rounding(rounding)
        step = Fraction(self.resolution)
        quotient = (as_fraction(value) - Fraction(as_decimal(self.offset))) / step
        coded = fit(round_exact(quotient, rounding), self.word_length, self.signed, mode)
        return coded + (1 << self.word_length) if coded < 0 else coded

    def decode(self, word: int) -> Decimal:
        """Return the exact real value of an unsigned ``word_length``-bit word.

        A negative ``word`` is accepted as an already-signed code when the layout is
        signed, so decoding round-trips whichever form the caller holds.
        """
        span = 1 << self.word_length
        if as_int(word, "word") < 0:
            if not self.signed or word < self._coded_min:
                raise FxpError(f"word {word} is out of range for this layout")
            word += span
        if word >= span:
            raise FxpError(f"word {word} does not fit {self.word_length} bits")
        return self._scale(word - span if self.signed and word > self._coded_max else word)

    def encode_many(self, values: Iterable[Number], **options: Unpack[EncodeOptions]) -> list[int]:
        """Encode each value with :meth:`encode` and the same keyword options."""
        return [self.encode(value, **options) for value in values]

    def decode_many(self, words: Iterable[int]) -> list[Decimal]:
        """Decode each word with :meth:`decode`, reusing this layout."""
        return [self.decode(word) for word in words]

    @property
    def byte_length(self) -> int:
        """Bytes in LabVIEW's flattened form: always 8 (see :meth:`pack`)."""
        return _flat.FLATTENED_SIZE

    @property
    def compact_byte_length(self) -> int:
        """Bytes in the compact, non-LabVIEW form: ``ceil(word_length / 8)``."""
        return _flat.compact_size(self.word_length)

    def pack(self, value: Number, **options: Unpack[EncodeOptions]) -> bytes:
        """Encode ``value`` and flatten it as LabVIEW does: 8 bytes, big-endian.

        The word sits in the low bits, sign extended when signed and zero extended when
        unsigned. Keyword options are those of :meth:`encode`.
        """
        word = self.encode(value, **options)
        return _flat.flatten_word(word, self.word_length, self.signed)

    def unpack(self, data: bytes | bytearray) -> Decimal:
        """Decode LabVIEW's 8-byte flattened form; the high bits must be the extension."""
        return self.decode(_flat.unflatten_word(data, self.word_length, self.signed))

    def pack_compact(self, value: Number, **options: Unpack[EncodeOptions]) -> bytes:
        """Encode ``value`` into ``compact_byte_length`` big-endian bytes.

        This is lvfxp's own dense form, not something LabVIEW reads or writes.
        """
        word = self.encode(value, **options)
        return _flat.compact_word(word, self.word_length)

    def unpack_compact(self, data: bytes | bytearray) -> Decimal:
        """Decode the compact form; bits above ``word_length`` are ignored."""
        return self.decode(_flat.uncompact_word(data, self.word_length))

    def pack_array(self, values: Iterable[Number], **options: Unpack[EncodeOptions]) -> bytes:
        """Flatten a 1-D array: a big-endian 32-bit count, then 8 bytes per element."""
        words = self.encode_many(values, **options)
        return _flat.flatten_array(words, self.word_length, self.signed)

    def unpack_array(self, data: bytes | bytearray) -> list[Decimal]:
        """Decode a flattened 1-D array written by :meth:`pack_array` or LabVIEW."""
        return self.decode_many(_flat.unflatten_array(data, self.word_length, self.signed))
