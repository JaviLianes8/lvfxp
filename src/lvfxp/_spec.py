"""The public fixed-point specification: a layout plus its byte forms."""

from __future__ import annotations

import copyreg
import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from . import _flat
from ._layout import Layout
from ._numbers import Bytes, Number
from ._quantize import LV_ROUND_HALF_EVEN


@dataclass(frozen=True, init=False)
class FxpSpec(Layout):
    """A LabVIEW fixed-point layout: ``<signed, word_length, integer_word_length>``.

    The word holds ``word_length`` bits (1 to 64), two's complement when ``signed``. Its
    real value is ``offset + coded * resolution``, where ``coded`` is the word read as an
    integer and ``resolution`` defaults to ``2 ** (integer_word_length - word_length)``.
    ``integer_word_length`` may exceed ``word_length`` or be negative (down to -4096, up to
    4096). ``delta`` and ``offset`` describe a general fixed-point layout; both are stored as
    ``Decimal``. Specs are immutable, hashable and compare by their fields.

    >>> spec = FxpSpec(word_length=8, integer_word_length=5)
    >>> spec.resolution, spec.min_value, spec.max_value
    (Decimal('0.125'), Decimal('-16.000'), Decimal('15.875'))
    >>> FxpSpec(8, 8, signed=False, delta="0.1", offset=1).decode(5)
    Decimal('1.5')
    """

    def __reduce__(self) -> tuple[object, ...]:
        # Every dataclass field (a subclass's too) and nothing derived; no __init__ on load.
        state = {field.name: getattr(self, field.name) for field in dataclasses.fields(self)}
        return copyreg.__newobj__, (type(self),), state  # type: ignore[attr-defined]

    def __setstate__(self, state: dict[str, object]) -> None:
        # Also reads pickles written by 0.3.0, whose state is the same five fields.
        for name, value in state.items():
            object.__setattr__(self, name, value)
        self.__post_init__()

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

    @property
    def byte_length(self) -> int:
        """Bytes in LabVIEW's flattened form: always 8 (see :meth:`pack`).

        >>> FxpSpec(12, 4).byte_length
        8
        """
        return _flat.FLATTENED_SIZE

    @property
    def compact_byte_length(self) -> int:
        """Bytes in the compact, non-LabVIEW form: ``ceil(word_length / 8)``.

        >>> FxpSpec(12, 4).compact_byte_length
        2
        """
        return _flat.compact_size(self.word_length)

    def pack(
        self,
        value: Number,
        *,
        clamp: bool = False,
        overflow: str = "raise",
        rounding: str = LV_ROUND_HALF_EVEN,
    ) -> bytes:
        """Encode ``value`` and flatten it as LabVIEW does: 8 bytes, big-endian.

        The word sits in the low bits, sign extended when signed and zero extended when
        unsigned. Keyword options are those of :meth:`encode`.

        >>> FxpSpec(8, 5).pack("-16").hex()
        'ffffffffffffff80'
        """
        word = self.encode(value, clamp=clamp, overflow=overflow, rounding=rounding)
        return _flat.flatten_word(word, self.word_length, self.signed)

    def unpack(self, data: Bytes) -> Decimal:
        """Decode LabVIEW's 8-byte flattened form; the high bits must be the extension.

        >>> FxpSpec(10, 4, signed=False).unpack(bytes.fromhex("00000000000003e5"))
        Decimal('15.578125')
        """
        return self.decode(_flat.unflatten_word(data, self.word_length, self.signed))

    def pack_compact(
        self,
        value: Number,
        *,
        clamp: bool = False,
        overflow: str = "raise",
        rounding: str = LV_ROUND_HALF_EVEN,
    ) -> bytes:
        """Encode ``value`` into ``compact_byte_length`` big-endian bytes.

        This is lvfxp's own dense form, not something LabVIEW reads or writes.

        >>> FxpSpec(4, 3).pack_compact("-2.5")
        b'\\x0b'
        """
        word = self.encode(value, clamp=clamp, overflow=overflow, rounding=rounding)
        return _flat.compact_word(word, self.word_length)

    def unpack_compact(self, data: Bytes) -> Decimal:
        """Decode the compact form; bits above ``word_length`` are ignored.

        >>> FxpSpec(4, 3).unpack_compact(bytes.fromhex("fb"))
        Decimal('-2.5')
        """
        return self.decode(_flat.uncompact_word(data, self.word_length))

    def pack_array(
        self,
        values: Iterable[Number],
        *,
        clamp: bool = False,
        overflow: str = "raise",
        rounding: str = LV_ROUND_HALF_EVEN,
    ) -> bytes:
        """Flatten a 1-D array: a big-endian 32-bit count, then 8 bytes per element.

        >>> FxpSpec(8, 5).pack_array([1, -1]).hex()
        '000000020000000000000008fffffffffffffff8'
        """
        words = self.encode_many(values, clamp=clamp, overflow=overflow, rounding=rounding)
        return _flat.flatten_array(words, self.word_length, self.signed)

    def unpack_array(self, data: Bytes) -> list[Decimal]:
        """Decode a flattened 1-D array written by :meth:`pack_array`.

        >>> FxpSpec(8, 5).unpack_array(bytes.fromhex("00000001fffffffffffffff8"))
        [Decimal('-1.000')]
        """
        return self.decode_many(_flat.unflatten_array(data, self.word_length, self.signed))


# The value math lives on the private base class; name it after the public class everywhere a
# caller can see it (tracebacks, TypeError messages for a bad keyword, help()).
for _name, _member in vars(Layout).items():
    _function = _member.fget if isinstance(_member, property) else _member
    if callable(_function) and hasattr(_function, "__qualname__"):
        _function.__qualname__ = f"FxpSpec.{_name}"
        _function.__module__ = FxpSpec.__module__
