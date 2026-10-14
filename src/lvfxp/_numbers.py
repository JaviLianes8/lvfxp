"""Strict, exact conversion of user input, and short, safe descriptions for error messages."""

from __future__ import annotations

import operator
import re
from collections.abc import Iterable, Iterator
from decimal import Context, Decimal, InvalidOperation
from fractions import Fraction
from typing import TypeVar, cast

from ._errors import FxpError

Number = int | float | Decimal | str
T = TypeVar("T")
Bytes = bytes | bytearray | memoryview

MAX_EXPONENT = 10_000
"""Largest decimal exponent accepted, so exact arithmetic stays bounded in time and memory."""

# An integer wider than this cannot be within MAX_EXPONENT decimal digits.
_MAX_BITS = 34_000
# Error messages never echo more than this many characters of a caller's value.
_SHOW_LIMIT = 40
_TYPE_NAME = type.__dict__["__name__"]
# Unambiguous (linear) grammar of a decimal number with an exponent.
_HUGE_EXPONENT = re.compile(r"\s*[+-]?(\d[\d_]*(?:\.[\d_]*)?|\.\d[\d_]*)[eE][+-]?\d[\d_]*\s*")


def type_name(value: object) -> str:
    """Return the real, bounded name of ``value``'s type, whatever a metaclass claims."""
    name = str.__add__("", _TYPE_NAME.__get__(type(value)))
    return name if len(name) <= _SHOW_LIMIT else name[:_SHOW_LIMIT] + "..."


def short(value: object) -> str:
    """Return a bounded description of ``value`` for an error message."""
    if issubclass(type(value), int) and type(value) is not bool:
        number = int.__index__(cast(int, value))
        if number.bit_length() > 64:
            return f"an integer of {number.bit_length()} bits"
        return str(number)
    try:
        text = str.__add__("", repr(value))
    except Exception:
        return f"a {type_name(value)} object"
    if len(text) > _SHOW_LIMIT:
        return f"{text[:_SHOW_LIMIT]}... ({len(text)} characters)"
    return text


def describe(number: int, noun: str) -> str:
    """Name an integer in a message: ``code 300``, or ``a code of 136 bits`` when it is wide."""
    bits = number.bit_length()
    return f"{noun} {number}" if bits <= 64 else f"a {noun} of {bits} bits"


def _parse(value: str | int, name: str) -> Decimal:
    if issubclass(type(value), int):
        number = int.__index__(cast(int, value))
        if number.bit_length() > _MAX_BITS:
            raise FxpError(f"{name} needs a decimal exponent beyond +/-{MAX_EXPONENT}")
        return Decimal(number)
    # A private context: the caller's traps and flags neither change nor see the result.
    try:
        return Decimal(str.__str__(value), Context(traps=[InvalidOperation]))
    except InvalidOperation:
        huge = _HUGE_EXPONENT.fullmatch(str.__str__(value))  # beyond what Decimal can hold
        if huge and not huge.group(1).strip("0._"):
            return Decimal(0)  # zero stays zero, whatever its exponent
        if huge:
            raise FxpError(f"{name} needs a decimal exponent beyond +/-{MAX_EXPONENT}") from None
        raise FxpError(f"{name} is not a number: {short(value)}") from None


def as_decimal(value: object, name: str = "value") -> Decimal:
    """Return ``value`` as a finite Decimal, without inheriting binary float noise.

    A float is read through its shortest repr, so ``0.1`` becomes ``Decimal("0.1")``.
    Booleans, non-numeric text, NaN, infinities and decimal exponents beyond
    ``MAX_EXPONENT`` raise :class:`FxpError`.

    >>> as_decimal(0.1), as_decimal("1e3"), as_decimal(7)
    (Decimal('0.1'), Decimal('1E+3'), Decimal('7'))
    """
    kind = type(value)  # the real type: a faked __class__ must not pass a check
    if kind is bool:
        raise FxpError(f"{name} must be a number, not a bool")
    if issubclass(kind, Decimal):
        result = Decimal(cast(Decimal, value))
    elif issubclass(kind, float):
        result = Decimal(float.__repr__(value))
    elif issubclass(kind, (int, str)):
        result = _parse(cast("int | str", value), name)
    else:
        raise FxpError(f"{name} must be int, float, Decimal or str, not {type_name(value)}")
    if not result.is_finite():
        raise FxpError(f"{name} must be finite, got {short(value)}")
    exponent = int(result.as_tuple().exponent)
    if result.is_zero():
        return result if abs(exponent) <= MAX_EXPONENT else Decimal(0)
    if max(abs(exponent), abs(result.adjusted())) > MAX_EXPONENT:
        raise FxpError(f"{name} needs a decimal exponent beyond +/-{MAX_EXPONENT}")
    return result


def as_fraction(value: object, name: str = "value") -> Fraction:
    """Return ``value`` as an exact Fraction (see :func:`as_decimal` for what is accepted)."""
    return Fraction(as_decimal(value, name))


def as_int(value: object, name: str) -> int:
    """Return ``value`` as a plain int; bools, floats and other non-integers raise FxpError.

    Any integer type (``int`` subclasses, NumPy integers) is accepted through ``__index__``.
    """
    kind = type(value)  # floats, Decimal, Fraction and text have no __index__
    if kind is bool or getattr(kind, "__index__", None) is None:
        raise FxpError(f"{name} must be an int, not {type_name(value)}")
    return int.__index__(operator.index(value))  # type: ignore[arg-type]


def as_items(values: Iterable[T], name: str) -> Iterator[T]:
    """Iterate ``values``; text, bytes-like objects and non-iterables raise FxpError."""
    if issubclass(type(values), (str, bytes, bytearray, memoryview)):
        raise FxpError(f"{name} must be an iterable of items, not {type_name(values)}")
    kind = type(values)
    iterate = getattr(kind, "__iter__", False)  # None means "not iterable", as in Python
    if iterate is None or (iterate is False and getattr(kind, "__getitem__", None) is None):
        raise FxpError(f"{name} must be an iterable, not {type_name(values)}")
    return iter(values)  # an error raised by the caller's own __iter__ propagates


def power_of_two(exponent: int) -> Decimal:
    """Return ``2 ** exponent`` exactly, without converting a big int to text."""
    if exponent >= 0:
        return Decimal(2**exponent)
    # 2**e == 5**-e * 10**e, exact in a private context wide enough for every digit.
    context = Context(prec=1 - exponent, Emax=999_999, Emin=-999_999)
    return context.scaleb(Decimal(5**-exponent), Decimal(exponent))


def digits(value: Decimal) -> int:
    """Upper bound on the significant digits needed to hold ``value`` exactly."""
    parts = value.as_tuple()
    return len(parts.digits) + abs(int(parts.exponent))
