"""Strict, exact conversion of user input into Decimal and Fraction."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction

from ._errors import FxpError

Number = int | float | Decimal | str


def as_decimal(value: object, name: str = "value") -> Decimal:
    """Return ``value`` as a finite Decimal, without inheriting binary float noise.

    A float is read through its shortest repr, so ``0.1`` becomes ``Decimal("0.1")``.
    Booleans, non-numeric text, NaN and infinities raise :class:`FxpError`.
    """
    if isinstance(value, bool):
        raise FxpError(f"{name} must be a number, not a bool")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, float):
        result = Decimal(repr(value))
    elif isinstance(value, (int, str)):
        try:
            result = Decimal(value)
        except InvalidOperation:
            raise FxpError(f"{name} is not a number: {value!r}") from None
    else:
        raise FxpError(f"{name} must be int, float, Decimal or str, not {type(value).__name__}")
    if not result.is_finite():
        raise FxpError(f"{name} must be finite, got {value!r}")
    return result


def as_fraction(value: object, name: str = "value") -> Fraction:
    """Return ``value`` as an exact Fraction (see :func:`as_decimal` for what is accepted)."""
    return Fraction(as_decimal(value, name))


def as_int(value: object, name: str) -> int:
    """Return ``value`` if it is a plain int (not a bool), else raise :class:`FxpError`."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise FxpError(f"{name} must be an int, not {type(value).__name__}")
    return value


def digits(value: Decimal) -> int:
    """Upper bound on the significant digits needed to hold ``value`` exactly."""
    parts = value.as_tuple()
    return len(parts.digits) + abs(int(parts.exponent))
