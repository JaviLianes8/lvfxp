"""Command line interface: encode and decode fixed-point words from a shell."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from decimal import (
    ROUND_05UP,
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
)

from . import __version__
from ._errors import FxpError
from ._spec import FxpSpec

_ROUNDING = {
    "half_even": ROUND_HALF_EVEN,
    "half_up": ROUND_HALF_UP,
    "half_down": ROUND_HALF_DOWN,
    "ceiling": ROUND_CEILING,
    "floor": ROUND_FLOOR,
    "up": ROUND_UP,
    "down": ROUND_DOWN,
    "05up": ROUND_05UP,
}

_EXAMPLES = """\
examples:
  lvfxp encode 15.875 --wl 8 --iwl 5            -> 7f
  lvfxp encode -2.5 --wl 4 --iwl 3 --word       -> 11
  lvfxp encode 16 --wl 8 --iwl 5 --clamp        -> 7f
  lvfxp decode 7f --wl 8 --iwl 5                -> 15.875
  lvfxp decode 80 --wl 8 --iwl 5                -> -16.000
  lvfxp decode 80 --wl 8 --iwl 5 --unsigned     -> 16.000
"""


def _add_spec(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--wl", type=int, required=True, help="word length in bits")
    parser.add_argument("--iwl", type=int, required=True, help="integer word length in bits")
    parser.add_argument(
        "--unsigned", action="store_true", help="read the word as unsigned (default: signed)"
    )
    parser.add_argument("--delta", help="explicit resolution for a general fixed-point layout")
    parser.add_argument("--offset", default="0", help="value added after scaling (default: 0)")


def _spec(args: argparse.Namespace) -> FxpSpec:
    return FxpSpec(args.wl, args.iwl, not args.unsigned, delta=args.delta, offset=args.offset)


def _parse_hex(text: str) -> bytes:
    cleaned = text.strip().removeprefix("0x").removeprefix("0X").replace("_", "").replace(" ", "")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise FxpError(f"not valid hex: {text!r}") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvfxp",
        description="Encode and decode LabVIEW fixed-point (FXP) numbers.",
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvfxp {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode = subparsers.add_parser("encode", help="turn a value into a fixed-point word")
    encode.add_argument("value", help="the real value to encode")
    encode.add_argument("--word", action="store_true", help="print the integer word, not hex")
    encode.add_argument("--clamp", action="store_true", help="saturate instead of overflowing")
    encode.add_argument("--rounding", choices=sorted(_ROUNDING), default="half_even")
    _add_spec(encode)

    decode = subparsers.add_parser("decode", help="turn a fixed-point word into a value")
    decode.add_argument("hex", nargs="?", help="flattened word as big-endian hex")
    decode.add_argument("--word", type=int, help="decode this integer word instead of hex")
    _add_spec(decode)
    return parser


def _run_encode(args: argparse.Namespace) -> str:
    spec = _spec(args)
    if args.word:
        return str(spec.encode(args.value, clamp=args.clamp, rounding=_ROUNDING[args.rounding]))
    return spec.pack(args.value, clamp=args.clamp, rounding=_ROUNDING[args.rounding]).hex()


def _run_decode(args: argparse.Namespace) -> str:
    spec = _spec(args)
    if args.word is not None:
        return str(spec.decode(args.word))
    if args.hex is None:
        raise FxpError("give a hex word or use --word")
    return str(spec.unpack(_parse_hex(args.hex)))


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvfxp`` console command."""
    args = _build_parser().parse_args(argv)
    try:
        output = _run_encode(args) if args.command == "encode" else _run_decode(args)
    except (FxpError, ValueError) as exc:
        print(f"lvfxp: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
