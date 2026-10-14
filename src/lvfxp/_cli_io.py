"""Command line plumbing: bounded usage errors and quiet exits when a pipe goes away."""

from __future__ import annotations

import argparse
import os
import sys
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from _typeshed import SupportsWrite

# Usage and data error messages are cut here, so a huge argument is never echoed back.
MESSAGE_LIMIT = 300


def silence(stream: object) -> None:
    """Point ``stream``'s descriptor at the null device after its reader went away.

    Python flushes the streams at exit; on a closed pipe that flush fails and the process
    exits 120 with a warning. Redirecting the descriptor makes every later write succeed.
    Only the failing stream is touched.
    """
    try:
        fd = stream.fileno()  # type: ignore[attr-defined]
    except (AttributeError, OSError, ValueError):
        return
    null = os.open(os.devnull, os.O_WRONLY)
    if null != fd:  # a closed fd is reused by open(): then it already is the null device
        os.dup2(null, fd)
        os.close(null)


def finish(code: int) -> int:
    """Flush both streams and return ``code``; a stream whose reader left is silenced."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (AttributeError, OSError, ValueError):
            silence(stream)
    return code


def write(stream_name: str, text: str) -> bool:
    """Write ``text`` to stdout or stderr; return False when the reader went away."""
    stream = sys.stdout if stream_name == "stdout" else sys.stderr
    try:
        stream.write(text)
        stream.flush()
    except (AttributeError, OSError, ValueError):
        silence(stream)
        return False
    return True


class Parser(argparse.ArgumentParser):
    """An argument parser whose errors are bounded and survive a closed stderr."""

    def error(self, message: str) -> NoReturn:
        if len(message) > MESSAGE_LIMIT:
            message = message[:MESSAGE_LIMIT] + "..."
        self.exit(2, f"{self.format_usage()}{self.prog}: error: {message}\n")

    lost_output = False  # set on the instance when help or version text could not be written

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if message:
            write("stderr", message)
        raise SystemExit(finish(1 if status == 0 and self.lost_output else status))

    def _print_message(self, message: str, file: SupportsWrite[str] | None = None) -> None:
        if message and not write("stderr" if file is sys.stderr else "stdout", message):
            self.lost_output = True
