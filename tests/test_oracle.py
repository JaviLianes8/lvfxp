"""Seeded random layouts, values and bytes checked against an independent rational oracle."""

from __future__ import annotations

import contextlib
import math
import random
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_HALF_DOWN, ROUND_UP, Decimal
from fractions import Fraction

import pytest

from lvfxp import (
    LV_ROUND_HALF_EVEN,
    LV_ROUND_HALF_UP,
    LV_TRUNCATE,
    FxpError,
    FxpOverflowError,
    FxpSpec,
)

_SEEDS = range(12)


def _layout(rng: random.Random) -> tuple[int, int, bool]:
    wl = rng.choice([1, 2, 7, 8, 9, 16, 31, 32, 33, 52, 53, 63, 64, rng.randint(1, 64)])
    return wl, rng.randint(-80, 80), rng.random() < 0.6


def _round(q: Fraction, mode: str) -> int:
    low = math.floor(q)
    if q == low:
        return low
    high = low + 1
    if mode == LV_TRUNCATE:
        return low
    if mode == ROUND_CEILING:
        return high
    if mode == ROUND_DOWN:
        return math.trunc(q)
    if mode == ROUND_UP:
        return high if q > 0 else low
    rest = q - low
    if rest != Fraction(1, 2):
        return low if rest < Fraction(1, 2) else high
    if mode == LV_ROUND_HALF_UP:
        return high
    if mode == ROUND_HALF_DOWN:
        return math.trunc(q)
    return low if low % 2 == 0 else high


def _range(wl: int, signed: bool) -> tuple[int, int]:
    return (-(1 << (wl - 1)), (1 << (wl - 1)) - 1) if signed else (0, (1 << wl) - 1)


def _text(value: Fraction, rng: random.Random) -> str:
    digits = rng.randint(0, 40)
    scaled = round(value * 10**digits)
    sign = "-" if scaled < 0 else ""
    body = str(abs(scaled)).rjust(digits + 1, "0")
    return (
        f"{sign}{body[: len(body) - digits]}.{body[len(body) - digits :]}"
        if digits
        else f"{sign}{body}"
    )


@pytest.mark.parametrize("seed", _SEEDS)
def test_decode_and_bytes_match_the_oracle(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(400):
        wl, iwl, signed = _layout(rng)
        spec = FxpSpec(wl, iwl, signed)
        low, high = _range(wl, signed)
        coded = rng.choice([low, high, 0, rng.randint(low, high)])
        word = coded % (1 << wl)
        value = spec.decode(word)
        assert Fraction(value) == coded * Fraction(2) ** (iwl - wl)
        flat = (coded % (1 << 64)).to_bytes(8, "big")
        assert spec.pack(value) == flat
        assert spec.unpack(flat) == value
        assert spec.encode(value) == word
        assert spec.unpack_compact(word.to_bytes((wl + 7) // 8, "big")) == value


@pytest.mark.parametrize("seed", _SEEDS)
def test_encode_rounds_and_overflows_like_the_oracle(seed: int) -> None:
    rng = random.Random(1000 + seed)
    modes = [LV_ROUND_HALF_EVEN, LV_ROUND_HALF_UP, LV_TRUNCATE, ROUND_CEILING, ROUND_DOWN]
    modes += [ROUND_UP, ROUND_HALF_DOWN]
    for _ in range(300):
        wl, iwl, signed = _layout(rng)
        spec = FxpSpec(wl, iwl, signed)
        low, high = _range(wl, signed)
        step = Fraction(2) ** (iwl - wl)
        q = Fraction(rng.randint(2 * low - 6, 2 * high + 6), 2) + Fraction(rng.randint(-3, 3), 7)
        text = _text(q * step, rng)
        exact = Fraction(Decimal(text)) / step
        mode = rng.choice(modes)
        code = _round(exact, mode)
        if low <= code <= high:
            assert spec.encode(text, rounding=mode) == code % (1 << wl)
            continue
        with pytest.raises(FxpOverflowError):
            spec.encode(text, rounding=mode)
        nearest = min(max(code, low), high)
        assert spec.encode(text, rounding=mode, overflow="saturate") == nearest % (1 << wl)
        assert spec.encode(text, rounding=mode, overflow="wrap") == code % (1 << wl)


@pytest.mark.parametrize("seed", _SEEDS)
def test_general_layouts_match_the_oracle(seed: int) -> None:
    rng = random.Random(2000 + seed)
    for _ in range(200):
        wl, signed = rng.randint(1, 64), rng.random() < 0.5
        delta = Fraction(rng.randint(1, 999), rng.choice([1, 10, 100, 7, 3]))
        offset = Fraction(rng.randint(-999, 999), rng.choice([1, 4, 1000]))
        delta_text, offset_text = _text(delta, rng), _text(offset, rng)
        d, o = Fraction(Decimal(delta_text)), Fraction(Decimal(offset_text))
        if d <= 0:
            continue
        spec = FxpSpec(wl, 0, signed, delta=delta_text, offset=offset_text)
        low, high = _range(wl, signed)
        coded = rng.randint(low, high)
        assert Fraction(spec.decode(coded % (1 << wl))) == o + coded * d
        value = o + (coded + Fraction(rng.randint(-49, 49), 100)) * d
        text = _text(value, rng)
        expected = _round((Fraction(Decimal(text)) - o) / d, LV_ROUND_HALF_EVEN)
        if low <= expected <= high:
            assert spec.encode(text) == expected % (1 << wl)
        else:
            with pytest.raises(FxpOverflowError):
                spec.encode(text)


@pytest.mark.parametrize("seed", _SEEDS)
def test_random_bytes_decode_or_raise_fxp_error(seed: int) -> None:
    rng = random.Random(3000 + seed)
    for _ in range(500):
        wl, iwl, signed = _layout(rng)
        spec = FxpSpec(wl, iwl, signed)
        data = rng.randbytes(rng.choice([0, 1, 4, 7, 8, 8, 8, 9, 12, 20]))
        for read in (spec.unpack, spec.unpack_compact, spec.unpack_array):
            with contextlib.suppress(FxpError):
                read(data)
