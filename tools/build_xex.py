#!/usr/bin/env python3
"""Build heartlight.xex: the game as a standalone Atari DOS binary load file.

Tajemnice ATARI promised "a program to save the finished game as a standalone file
(without the BASIC part)" for the next issue. This is that program. The XEX recreates
exactly the memory state the BASIC loader (lines 10-400 of the listing) leaves behind
before `X=USR(PLAY)`:

  $02C4-$02C8  COLOR0..COLOR4 shadows        line 220  (POKE 708..712)
  $7000-$7002  lives, extra, room count      line 230
  $7003-$7016  title banner (20 bytes)       line 240, first '/' string
  $7017-...    rooms, 240 bytes each         line 240, remaining '/' strings
  $9014-$9907  game code + charset           lines 100-130 (hex DATA via RHEX)
  $00D0        TICK = $4B                    residue of RHEX's checksum accumulator (see SPEC 4.2)
  $02E0-$02E1  RUNAD = PLAY ($9260)          line 400

The page-6 loader routines are not needed at run time and are left out. Load with any
DOS ("L" binary load) or XEX loader on a real machine or in an emulator.

--saver writes instead the exact file layout of the magazine's own tool, the short
"Heartlight Saver" (Mirosław Liminowicz, TA 2/91, SHORTHSV.LST): RUNAD, the colour
shadows, $9000-$98FF as the game leaves it (the first 20 bytes zeroed by TITLE_CONV)
and the level data. That tool was run after RESET at the title screen, so it does not
set $D0; the default layout does (see SPEC 4.2).

Usage: python3 tools/build_xex.py [-o heartlight.xex] [--data DIR] [--saver]
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLOR0, CAV, LOAD_ADDR, PLAY, RUNAD, TICK = 0x02C4, 0x7000, 0x9014, 0x9260, 0x02E0, 0x00D0
CHARSET, SAVER_END = 0x9000, 0x98FF          # SHORTHSV.LST line 2020: segment $9000-$98FF
ROOM_W, ROOM_H = 20, 12


def segment(start: int, data: bytes) -> bytes:
    return struct.pack('<HH', start, start + len(data) - 1) + data


def level_block(data_dir: Path) -> tuple[bytes, bytes, bytes]:
    """(colours 708..712, params + banner + rooms, game.bin)."""
    meta = json.loads((data_dir / 'meta.json').read_text())
    text = (data_dir / 'levels.txt').read_text()
    m = re.search(r'^; title banner: \[(.{20})\]', text, re.M)
    banner = m.group(1) if m else ' ' * ROOM_W
    rows = [ln for ln in text.splitlines() if len(ln) == ROOM_W and not ln.startswith(';')]
    if len(rows) != meta['rooms'] * ROOM_H:
        sys.exit(f'levels.txt: expected {meta["rooms"] * ROOM_H} rows, found {len(rows)}')
    game = (data_dir / 'game.bin').read_bytes()
    colors = bytes(meta['colors_708_712'])
    level_data = bytes([meta['lives'], meta['extra'], meta['rooms']]) + banner.encode('latin-1') \
        + ''.join(rows).encode('latin-1')
    return colors, level_data, game


def build(data_dir: Path) -> bytes:
    colors, level_data, game = level_block(data_dir)
    return (b'\xff\xff'
            + segment(COLOR0, colors)
            + segment(CAV, level_data)
            + segment(LOAD_ADDR, game)
            + segment(TICK, bytes([0x4B]))
            + segment(RUNAD, struct.pack('<H', PLAY)))


def build_saver(data_dir: Path) -> bytes:
    """SHORTHSV.LST: header (line 2010/2020, colours POKEd at GAM-9), $9000-$98FF, then the
    level data with the 4-byte header of line 110 ($7000 .. CAV+CL-1, CL = rooms*240+23)."""
    colors, level_data, game = level_block(data_dir)
    code = bytes(LOAD_ADDR - CHARSET) + game                  # $9000..$9013 are zero after TITLE_CONV
    code = code[:SAVER_END - CHARSET + 1]                     # the saver stops at $98FF (zeros beyond)
    return (b'\xff\xff'
            + segment(RUNAD, struct.pack('<H', PLAY))
            + segment(COLOR0, colors)
            + segment(CHARSET, code)
            + segment(CAV, level_data))


def parse(xex: bytes) -> list[tuple[int, int, bytes]]:
    """DOS binary format: optional $FFFF marker(s), then (start, end, data) segments."""
    out, i = [], 0
    while i < len(xex):
        if xex[i:i + 2] == b'\xff\xff':
            i += 2
            continue
        start, end = struct.unpack('<HH', xex[i:i + 4])
        i += 4
        out.append((start, end, xex[i:i + end - start + 1]))
        i += end - start + 1
    return out


def load_into(mem, xex: bytes) -> int:  # type: ignore[no-untyped-def]
    """Poke every segment into a py65 memory; return RUNAD."""
    for start, _end, data in parse(xex):
        for k, b in enumerate(data):
            mem[start + k] = b
    return mem[RUNAD] | (mem[RUNAD + 1] << 8)


def main() -> None:
    ap = argparse.ArgumentParser(description='Build the standalone heartlight.xex')
    ap.add_argument('-o', '--output', type=Path, default=ROOT / 'heartlight.xex')
    ap.add_argument('--data', type=Path, default=ROOT, help='directory with game.bin, meta.json, levels.txt')
    ap.add_argument('--saver', action='store_true', help="the magazine's Heartlight Saver layout (SHORTHSV.LST)")
    args = ap.parse_args()
    xex = build_saver(args.data) if args.saver else build(args.data)
    args.output.write_bytes(xex)
    segs = parse(xex)
    print(f'{args.output}: {len(xex)} bytes, {len(segs)} segments')
    for start, end, data in segs:
        print(f'  ${start:04X}-${end:04X}  {len(data):5d} B')


if __name__ == '__main__':
    main()
