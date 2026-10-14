"""Exceptions raised by the fixed-point codec."""

from __future__ import annotations


class FxpError(ValueError):
    """Base class for every fixed-point encoding or decoding error; a ``ValueError``.

    >>> from lvfxp import FxpSpec
    >>> try:
    ...     FxpSpec(65, 0)
    ... except FxpError as error:
    ...     print(error)
    word_length must be between 1 and 64, got 65
    """


class FxpOverflowError(FxpError):
    """A value does not fit the layout's range and ``overflow`` is ``"raise"``.

    >>> from lvfxp import to_fxp
    >>> try:
    ...     to_fxp(16, 8, 5)
    ... except FxpOverflowError as error:
    ...     print(error)
    value needs code 128, outside [-128, 127]
    """
