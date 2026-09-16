#!/usr/bin/env python3
"""The two-letter line codes printed beside every line of a Tajemnice ATARI listing.

Algorithm recovered from the machine code of "Generator Kodów Kontrolnych" (Mirosław
Liminowicz, TA 2/91, https://tajemnice.atari8.info/2_91/2_91_generator.html): the program
hooks the GET vector of the E: handler; when BASIC reads a line (RETURN), it takes the bytes
the editor returned (the logical line as displayed, trailing blanks stripped, no EOL) and
computes

    v = (sum over i = 1..n of i * byte_i) mod 676
    code = chr(ord('A') + v // 26) + chr(ord('A') + v % 26)

    python3 tools/line_codes.py FAC.LST            # prints "code  line" for every line
    python3 tools/line_codes.py FAC.LST 1010 1140  # only that range
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EOL = 0x9B


def line_code(line: bytes) -> str:
    """`line` = the text BASIC receives from E:, e.g. b'1000 REM' (no EOL)."""
    body = line.rstrip(b' ')
    v = sum((i + 1) * b for i, b in enumerate(body)) % 676
    return chr(65 + v // 26) + chr(65 + v % 26)


def listing_codes(data: bytes) -> list[tuple[int, str, bytes]]:
    out = []
    for rec in data.split(bytes([EOL])):
        m = re.match(rb'^(\d+) ', rec)
        if m:
            out.append((int(m.group(1)), line_code(rec), rec))
    return out


def main(argv: list[str]) -> None:
    path = Path(argv[1] if len(argv) > 1 else 'FAC.LST')
    lo = int(argv[2]) if len(argv) > 2 else 0
    hi = int(argv[3]) if len(argv) > 3 else 10 ** 9
    for no, code, rec in listing_codes(path.read_bytes()):
        if lo <= no <= hi:
            text = ''.join(chr(b) if 0x20 <= b < 0x7F else f'\\x{b:02x}' for b in rec)
            print(f'{code}  {text}')


if __name__ == '__main__':
    main(sys.argv)
