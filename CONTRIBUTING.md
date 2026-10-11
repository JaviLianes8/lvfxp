# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/lvfxp/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Compute expected values independently (for
  example with `fractions.Fraction`), never by calling the library twice.
- Bytes in `tests/fixtures/labview2026` were written by a real LabVIEW; never edit them.
  Claims about LabVIEW's byte layout need such a capture or an NI document to cite.
- Run `scripts/check.ps1` and make sure it passes: `ruff format --check .`, `ruff check .`,
  `mypy --strict src` and `pytest` each exit 0. The end-to-end test installs the package
  editable and drives the real `lvfxp` script.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
