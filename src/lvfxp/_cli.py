"""Command line interface: encode, decode and describe fixed-point words from a shell."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from decimal import Decimal

from . import __version__
from ._errors import FxpError
from ._layout import EncodeOptions
from ._numbers import as_decimal, short
from ._quantize import LV_ROUND_HALF_EVEN, LV_ROUND_HALF_UP, LV_TRUNCATE, OVERFLOW_MODES
from ._spec import FxpSpec

_ROUNDING = {
    "half-even": LV_ROUND_HALF_EVEN,
    "half-up": LV_ROUND_HALF_UP,
    "truncate": LV_TRUNCATE,
}

_EXAMPLES = """\
examples:
  lvfxp encode 15.875 --wl 8 --iwl 5                    -> 000000000000007f
  lvfxp encode -2.5 --wl 4 --iwl 3                      -> fffffffffffffffb
  lvfxp encode -2.5 --wl 4 --iwl 3 --word               -> 11
  lvfxp encode 16 --wl 8 --iwl 5 --overflow saturate    -> 000000000000007f
  lvfxp encode 16 --wl 8 --iwl 5 --overflow wrap        -> ffffffffffffff80
  lvfxp encode -0.0625 --wl 8 --iwl 5 --rounding half-up -> 0000000000000000
  lvfxp encode 15.875 --wl 8 --iwl 5 --compact          -> 7f
  lvfxp decode ffffffffffffff80 --wl 8 --iwl 5          -> -16
  lvfxp decode 00000000000003e5 --wl 10 --iwl 4 --unsigned -> 15.578125
  lvfxp decode 7f --wl 8 --iwl 5 --compact              -> 15.875
  lvfxp decode --word 128 --wl 8 --iwl 5 --unsigned     -> 16
  lvfxp info --wl 8 --iwl 5                             (layout, resolution, range)

Flattened bytes are LabVIEW's form: 8 bytes, big-endian, the word in the low bits, sign
extended when signed and zero extended when unsigned. --compact uses ceil(wl / 8) bytes
instead, a dense form that LabVIEW itself does not read or write. Values with an overflow
status (9 bytes in LabVIEW) are not supported. Data errors print to stderr and exit 1.
Put -- before a negative value in scientific notation: lvfxp encode --wl 8 --iwl 5 -- -1e0
"""


def _add_spec(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--wl", type=int, required=True, help="word length in bits (1 to 64)")
    parser.add_argument("--iwl", type=int, required=True, help="integer word length in bits")
    parser.add_argument(
        "--unsigned", action="store_true", help="read the word as unsigned (default: signed)"
    )
    parser.add_argument("--delta", help="explicit resolution for a general fixed-point layout")
    parser.add_argument("--offset", default="0", help="value added after scaling (default: 0)")


def _spec(args: argparse.Namespace) -> FxpSpec:
    return FxpSpec(args.wl, args.iwl, not args.unsigned, delta=args.delta, offset=args.offset)


def _plain(value: Decimal) -> str:
    """Exact plain notation without exponent or trailing zeros."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _parse_hex(text: str) -> bytes:
    cleaned = text.strip().removeprefix("0x").removeprefix("0X").replace("_", "").replace(" ", "")
    try:
        return bytes.fromhex(cleaned)
    except ValueError:
        raise FxpError(f"not valid hex: {short(text)}") from None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvfxp",
        description="Encode and decode LabVIEW fixed-point (FXP) numbers exactly.",
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvfxp {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode = subparsers.add_parser("encode", help="turn a value into flattened bytes or a word")
    encode.add_argument("value", help="the real value to encode, for example 15.875")
    form = encode.add_mutually_exclusive_group()
    form.add_argument("--word", action="store_true", help="print the integer word, not hex")
    form.add_argument("--compact", action="store_true", help="print ceil(wl/8) bytes (not LabVIEW)")
    encode.add_argument(
        "--overflow", choices=OVERFLOW_MODES, default="raise", help="default: raise (exit 1)"
    )
    encode.add_argument("--clamp", action="store_true", help="same as --overflow saturate")
    encode.add_argument(
        "--rounding", choices=sorted(_ROUNDING), default="half-even", help="default: half-even"
    )
    _add_spec(encode)

    decode = subparsers.add_parser("decode", help="turn flattened bytes or a word into a value")
    decode.add_argument("hex", nargs="?", help="LabVIEW's 8 flattened bytes as big-endian hex")
    decode.add_argument("--word", type=int, help="decode this integer word instead of hex")
    decode.add_argument("--compact", action="store_true", help="read ceil(wl/8) bytes instead")
    _add_spec(decode)

    info = subparsers.add_parser("info", help="show a layout's resolution, range and sizes")
    _add_spec(info)
    return parser


def _run_encode(args: argparse.Namespace) -> str:
    spec = _spec(args)
    options: EncodeOptions = {
        "clamp": args.clamp,
        "overflow": args.overflow,
        "rounding": _ROUNDING[args.rounding],
    }
    if args.word:
        return str(spec.encode(args.value, **options))
    if args.compact:
        return spec.pack_compact(args.value, **options).hex()
    return spec.pack(args.value, **options).hex()


def _run_decode(args: argparse.Namespace) -> str:
    spec = _spec(args)
    if args.word is not None:
        if args.hex is not None:
            raise FxpError("give either hex bytes or --word, not both")
        return _plain(spec.decode(args.word))
    if args.hex is None:
        raise FxpError("give the flattened bytes as hex, or use --word")
    data = _parse_hex(args.hex)
    return _plain(spec.unpack_compact(data) if args.compact else spec.unpack(data))


def _run_info(args: argparse.Namespace) -> str:
    spec = _spec(args)
    sign = "+/-" if spec.signed else "+"
    if spec.delta is None:
        layout = [f"layout: <{sign}, {spec.word_length}, {spec.integer_word_length}>"]
    else:
        layout = [f"layout: <{sign}, {spec.word_length}> with an explicit delta"]
    if spec.offset != 0:
        layout.append(f"offset: {_plain(as_decimal(spec.offset))}")
    return "\n".join(
        [
            *layout,
            f"resolution: {_plain(spec.resolution)}",
            f"minimum: {_plain(spec.min_value)}",
            f"maximum: {_plain(spec.max_value)}",
            f"flattened bytes: {spec.byte_length}",
            f"compact bytes: {spec.compact_byte_length}",
        ]
    )


_COMMANDS = {"encode": _run_encode, "decode": _run_decode, "info": _run_info}


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvfxp`` console command."""
    args = _build_parser().parse_args(argv)
    try:
        output = _COMMANDS[args.command](args)
    except (FxpError, ValueError, ArithmeticError) as exc:
        print(f"lvfxp: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
