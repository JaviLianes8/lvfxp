"""Strict, exact conversion of user input, and short, safe descriptions for error messages."""

from __future__ import annotations

import operator
from decimal import Context, Decimal, InvalidOperation
from fractions import Fraction

from ._errors import FxpError

Number = int | float | Decimal | str
Bytes = bytes | bytearray | memoryview

MAX_EXPONENT = 10_000
"""Largest decimal exponent accepted, so exact arithmetic stays bounded in time and memory."""

# An integer wider than this cannot be within MAX_EXPONENT decimal digits.
_MAX_BITS = 34_000
# Error messages never echo more than this many characters of a caller's value.
_SHOW_LIMIT = 40
_TYPE_NAME = type.__dict__["__name__"]


def type_name(value: object) -> str:
    """Return the real, bounded name of ``value``'s type, whatever a metaclass claims."""
    name = str.__add__("", _TYPE_NAME.__get__(type(value)))
    return name if len(name) <= _SHOW_LIMIT else name[:_SHOW_LIMIT] + "..."


def short(value: object) -> str:
    """Return a bounded description of ``value`` for an error message."""
    if isinstance(value, int) and not isinstance(value, bool):
        number = int.__index__(value)
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


def _parse(value: str | int, name: str) -> Decimal:
    if isinstance(value, int):
        number = int.__index__(value)
        if number.bit_length() > _MAX_BITS:
            raise FxpError(f"{name} needs a decimal exponent beyond +/-{MAX_EXPONENT}")
        return Decimal(number)
    # A private context: the caller's traps and flags neither change nor see the result.
    try:
        return Decimal(str.__str__(value), Context(traps=[InvalidOperation]))
    except InvalidOperation:
        raise FxpError(f"{name} is not a number: {short(value)}") from None


def as_decimal(value: object, name: str = "value") -> Decimal:
    """Return ``value`` as a finite Decimal, without inheriting binary float noise.

    A float is read through its shortest repr, so ``0.1`` becomes ``Decimal("0.1")``.
    Booleans, non-numeric text, NaN, infinities and decimal exponents beyond
    ``MAX_EXPONENT`` raise :class:`FxpError`.

    >>> as_decimal(0.1), as_decimal("1e3"), as_decimal(7)
    (Decimal('0.1'), Decimal('1E+3'), Decimal('7'))
    """
    if isinstance(value, bool):
        raise FxpError(f"{name} must be a number, not a bool")
    if isinstance(value, Decimal):
        result = Decimal(value)
    elif isinstance(value, float):
        result = Decimal(float.__repr__(value))
    elif isinstance(value, (int, str)):
        result = _parse(value, name)
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
    if isinstance(value, (bool, float, Decimal, Fraction, str)):
        raise FxpError(f"{name} must be an int, not {type_name(value)}")
    try:
        number = operator.index(value)  # type: ignore[arg-type]
    except TypeError:
        raise FxpError(f"{name} must be an int, not {type_name(value)}") from None
    return int.__index__(number)


def digits(value: Decimal) -> int:
    """Upper bound on the significant digits needed to hold ``value`` exactly."""
    parts = value.as_tuple()
    return len(parts.digits) + abs(int(parts.exponent))
