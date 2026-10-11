# lvfxp: round 2 improvements

Ranked by impact on correctness first, then on usefulness. Items marked "done" ship in
this branch; the rest stay open.

## 1. Correct the flattened byte layout (done)

0.2.0 flattened a word into `ceil(word_length / 8)` bytes and called that LabVIEW's form.
It is not. NI documents that a fixed-point number has a 64-bit format and is sign extended
to 64 bits, that flattened numbers are big-endian, and that fixed-point takes 64 bits of
storage on disk (72 with an overflow status). A real LabVIEW 2026 capture agrees: every
fixed-point value in a front-panel datalog record is 8 bytes, the word in the low bits,
sign extended when signed and zero extended when unsigned. `pack`/`unpack` now read and
write that 8-byte form. The old compact form stays available under an explicit,
non-LabVIEW name (`pack_compact`/`unpack_compact`).

## 2. Say exactly what is verified (done)

The README separates the value math (word length, integer word length, signedness,
scaling, rounding, overflow) from the byte layout, cites the NI pages and the capture, and
states that the overflow-status form is not supported because its byte layout is not
documented and could not be captured.

## 3. Reject what LabVIEW cannot hold (done)

LabVIEW word lengths run from 1 to 64 bits. `FxpSpec` now rejects anything wider, and
rejects non-finite values, malformed numbers and non-integer words with `FxpError`
instead of leaking `decimal.InvalidOperation` (which also crashed the CLI with a
traceback).

## 4. LabVIEW rounding and overflow modes (done)

LabVIEW offers Truncate, Round-Half-Up (asymmetric, ties toward positive infinity) and
Round-Half-Even, and Saturate or Wrap on overflow. Python's `ROUND_HALF_UP` rounds ties
away from zero, so negative ties differed. New constants `LV_TRUNCATE`,
`LV_ROUND_HALF_UP` and `LV_ROUND_HALF_EVEN` match LabVIEW, and `overflow="wrap"` keeps the
low bits like LabVIEW's Wrap mode. Rounding is now exact over rationals, so an explicit
`delta` such as 0.3 can never double-round near a tie.

## 5. Flattened 1-D arrays (done)

`FxpSpec.pack_array`/`unpack_array` read and write a flattened 1-D fixed-point array: a
big-endian 32-bit element count followed by the 8-byte elements, per NI's array rules.

## 6. CLI polish (done)

`--compact` selects the non-LabVIEW form, `--overflow` and LabVIEW rounding names replace
the old Python-only choices, a new `info` command prints resolution and range, decoded
values print in plain notation (no exponent), and a 9-byte input explains that the
overflow-status form is unsupported.

## 7. Contract and real end-to-end tests (done)

A contract test sweeps every word of every layout up to 8 bits (signed and unsigned,
several integer word lengths) through value math, both byte forms and the array form. The
real-capture test decodes the LabVIEW 2026 datalog bytes. The end-to-end test installs the
package editable and drives the generated `lvfxp` console script.

## 8. Open

- Overflow-status form (72 bits): add only once a real capture shows where the status
  byte sits and how it is encoded.
- Integer word length bounds: LabVIEW limits them, but the exact range is not verified
  here, so lvfxp does not enforce one.
- Little-endian helpers for consumers that byte-swap after flattening.
