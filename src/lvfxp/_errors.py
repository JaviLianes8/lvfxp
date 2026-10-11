"""Exceptions raised by the fixed-point codec."""

from __future__ import annotations


class FxpError(ValueError):
    """Base class for every fixed-point encoding or decoding error."""


class FxpOverflowError(FxpError):
    """A value does not fit the fixed-point range and clamping is disabled."""
