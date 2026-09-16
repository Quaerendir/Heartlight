#!/usr/bin/env python3
"""
heartlight_extract.py -- Stage 1 of the Heartlight (Atari 8-bit, J. Pelc 1990,
Tajemnice ATARI) conversion pipeline.

Parses the BASIC XL loader listing and extracts:
  * levels.txt   -- room maps (20x12 ASCII) + title banner
  * meta.json    -- colors (708-712), lives/extra/room-count, memory layout
                    ($7000 params, $7003 title, $7017 rooms, 240 B each)
  * game.bin     -- 6502 machine code decoded from hex DATA lines
                    (load address $9014, entry PLAY = $9260), checksum-verified
  * loader.bin   -- page-6 helper routines decoded from decimal DATA lines

--extra FILE appends another listing the way ENTER "D:FILE" does (lines merged
by number, later files win): the eight rooms of "Komnaty do Heartlighta"
(Maciej Mach, TA 2/91, KOMNATY.LST) are DATA lines 1501..2212. --rooms N is
step 5 of that article: the third parameter of line 1050 (room count).

Checksum algorithm (recovered from the ML hex decoder at $0603):
  each hex DATA line = 26 hex chars = 13 bytes; byte[12] == sum(byte[0:12]) & 0xFF

Author: Quaerendir
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOM_W, ROOM_H = 20, 12
BEGN = 36864            # $9000
LOAD_ADDR = BEGN + 20   # $9014 -- hex payload lands here (see line 100: A=BEGN+20)
PLAY = BEGN + 608       # $9260 -- USR entry point (line 30 / 400)
CAV = 28672             # $7000 -- lives/extra/rooms (line 230), title at +3, rooms at +23 (line 240)
TITLE_ADDR = CAV + 3
ROOMS_ADDR = TITLE_ADDR + ROOM_W
MAX_ROOMS = 30          # documented limit (TA 1/91); 30*240 B from $7017 stays below the charset at $9000
ROOM_CHARS = set('%#@$*!&. ')
P6 = 1536               # $0600 -- loader routines

HEXLINE = re.compile(r'^[0-9a-fA-F]{26}$')


def logical_lines(text: str):
    """Re-join listing lines wrapped at ~38 cols.

    A physical line starts a new logical BASIC line iff it begins with
    '<digits> ' AND the number is greater than the previous line number
    (line numbers in the listing are strictly increasing). Anything else
    is a continuation -- this correctly handles wraps like 'GOTO 14\\n0'.
    """
    out, cur_no, cur = [], -1, None
    for phys in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        m = re.match(r'^(\d+) ', phys)
        if m and int(m.group(1)) > cur_no:
            if cur is not None:
                out.append((cur_no, cur))
            cur_no, cur = int(m.group(1)), phys[m.end():]
        elif cur is not None:
            cur += phys
    if cur is not None:
        out.append((cur_no, cur))
    return out


def data_payload(stmt: str):
    s = stmt.strip()
    if s.startswith('DATA'):
        return s[4:].strip()
    return None


def decode_hex_line(payload: str):
    """26 hex chars -> (12 payload bytes, checksum_ok)."""
    b = bytes.fromhex(payload)
    return b[:12], (sum(b[:12]) & 0xFF) == b[12]


def validate_room(n: int, rows: list[str]) -> list[str]:
    """Sanity checks the loader cannot do: room strings carry no checksum."""
    warn = []
    grid = ''.join(rows)
    bad = sorted(set(grid) - ROOM_CHARS)
    if bad:
        warn.append(f'unknown chars {bad} (the game turns them into rocks)')
    if grid.count('*') == 0:
        warn.append('no hero')
    if grid.count('!') != 1:
        warn.append(f'{grid.count("!")} exits')
    if grid.count('$') == 0:
        warn.append('no hearts')
    border = rows[0] + rows[-1] + ''.join(r[0] + r[-1] for r in rows)
    if set(border) - set('%!'):
        warn.append('frame is not solid % (grid edge is solid in-game, so this may be intended)')
    return [f'room {n}: {w}' for w in warn]


def glyph_dump(blob: bytes, offset: int, count: int):
    """Render 8-byte glyphs as ASCII art -- exploration aid for locating
    the redefined charset / tile bitmaps inside game.bin."""
    lines = []
    for g in range(count):
        base = offset + g * 8
        if base + 8 > len(blob):
            break
        lines.append(f'--- glyph {g} @ bin+{base:#06x} (mem ${LOAD_ADDR + base:04X}) ---')
        for row in blob[base:base + 8]:
            lines.append(''.join('#' if row & (0x80 >> i) else '.' for i in range(8)))
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description='Extract data from heartlight.bas')
    ap.add_argument('source', type=Path)
    ap.add_argument('-o', '--outdir', type=Path, default=Path('.'))
    ap.add_argument('--extra', type=Path, action='append', default=[], metavar='FILE',
                    help='ENTER another listing on top (e.g. KOMNATY.LST with rooms 5..12)')
    ap.add_argument('--rooms', type=int, default=None, help='override the room count of line 1050')
    ap.add_argument('--glyphs', metavar='OFF[,N]',
                    help='dump N (default 16) 8-byte glyphs from game.bin at offset OFF (hex ok)')
    args = ap.parse_args()

    text = args.source.read_text(encoding='latin-1')
    lines = logical_lines(text)
    for extra in args.extra:                                   # ENTER "D:...": merge by line number
        merged = dict(lines)
        merged.update(logical_lines(extra.read_text(encoding='latin-1').replace('\x9b', '\n')))
        lines = sorted(merged.items())

    colors, params, strings, hex_rows, loader_vals = [], [], [], [], []
    bad_checksums, bad_hex = [], []

    for no, body in lines:
        payload = data_payload(body)
        if payload is None:
            continue
        if payload.startswith('/'):
            row = payload[1:1 + ROOM_W].ljust(ROOM_W)          # ML copies 20 bytes past the '/'
            if payload[1 + ROOM_W:2 + ROOM_W] != '/':
                print(f'!! line {no}: expected /<{ROOM_W} chars>/, closing slash not at position {ROOM_W + 1}',
                      file=sys.stderr)
            strings.append((no, row))
        elif no >= 10000:
            if HEXLINE.match(payload):
                chunk, ok = decode_hex_line(payload)
                hex_rows.append(chunk)
                if not ok:
                    bad_checksums.append(no)
            else:
                bad_hex.append(no)                             # a dropped line would shift all following code
        elif no == 1030:
            colors = [int(v) for v in payload.split(',')]
        elif no == 1050:
            params = [int(v) for v in payload.split(',')]
            if args.rooms is not None and len(params) == 3:    # "uaktualnić trzeci parametr w wierszu 1050"
                params[2] = args.rooms
        elif 500 <= no < 1000:
            loader_vals += [int(v) for v in payload.split(',')]

    if bad_hex:
        print(f'!! malformed hex DATA (not 26 hex chars) on BASIC lines: {bad_hex}', file=sys.stderr)
    if bad_checksums:
        print(f'!! checksum FAILED on BASIC lines: {bad_checksums}', file=sys.stderr)
    if len(params) != 3:
        sys.exit(f'parse error: line 1050 must hold 3 values (lives, extra, rooms), got {params}')
    if len(strings) < 2:
        sys.exit('parse error: need the title string (line 1070) and at least one room row')

    lives, extra, n_rooms = params
    title, rows = strings[0][1], strings[1:]
    if n_rooms > MAX_ROOMS:
        print(f'!! {n_rooms} rooms exceeds the game limit of {MAX_ROOMS}', file=sys.stderr)
    if len(rows) < n_rooms * ROOM_H:
        sys.exit(f'parse error: expected {n_rooms * ROOM_H} room rows, got {len(rows)}')
    if len(rows) > n_rooms * ROOM_H:
        print(f'!! {len(rows) - n_rooms * ROOM_H} extra room rows ignored (line 1050 says {n_rooms} rooms)',
              file=sys.stderr)
    for r in range(n_rooms):
        for w in validate_room(r + 1, [row for _, row in rows[r * ROOM_H:(r + 1) * ROOM_H]]):
            print(f'!! {w}', file=sys.stderr)

    args.outdir.mkdir(parents=True, exist_ok=True)

    # levels.txt
    with open(args.outdir / 'levels.txt', 'w') as f:
        f.write('; HEARTLIGHT (C) 1990 Janusz Pelc / Tajemnice ATARI\n')
        f.write(f'; title banner: [{title}]\n')
        f.write(f'; legend: % hard-wall  # soft-wall  @ rock  $ heart  * hero'
                f'  ! exit  & bomb  . grass  (space) empty\n')
        for r in range(n_rooms):
            f.write(f'\n[room {r + 1}]\n')
            for y in range(ROOM_H):
                f.write(rows[r * ROOM_H + y][1] + '\n')

    # game.bin + loader.bin
    game = b''.join(hex_rows)
    (args.outdir / 'game.bin').write_bytes(game)
    stop = loader_vals.index(-1) if -1 in loader_vals else len(loader_vals)
    (args.outdir / 'loader.bin').write_bytes(bytes(loader_vals[:stop]))

    # meta.json
    meta = {
        'source': args.source.name,
        'extra_sources': [e.name for e in args.extra],
        'colors_708_712': colors,
        'lives': lives, 'extra': extra, 'rooms': n_rooms,
        'game_bin': {
            'size': len(game),
            'load_addr': f'${LOAD_ADDR:04X}',
            'entry_PLAY': f'${PLAY:04X}',
            'entry_offset_in_bin': PLAY - LOAD_ADDR,
            'checksum_failures': bad_checksums,
        },
        'loader_bin': {'size': stop, 'load_addr': f'${P6:04X}'},
        'data_layout': {
            'params_addr': f'${CAV:04X}',          # lives, extra, rooms (1 byte each)
            'title_addr': f'${TITLE_ADDR:04X}',    # 20 bytes
            'rooms_addr': f'${ROOMS_ADDR:04X}',    # n_rooms * 240 bytes, row-major 20x12
            'room_size': ROOM_W * ROOM_H,
        },
    }
    (args.outdir / 'meta.json').write_text(json.dumps(meta, indent=2) + '\n')

    print(f'OK: {n_rooms} rooms, game.bin {len(game)} B '
          f'(load ${LOAD_ADDR:04X}, PLAY ${PLAY:04X} = bin+{PLAY - LOAD_ADDR:#x}), '
          f'loader.bin {stop} B, checksums: '
          f'{"ALL PASS" if not bad_checksums else f"{len(bad_checksums)} FAILED"}')

    if args.glyphs:
        parts = args.glyphs.split(',')
        off = int(parts[0], 0)
        cnt = int(parts[1], 0) if len(parts) > 1 else 16
        print(glyph_dump(game, off, cnt))


if __name__ == '__main__':
    main()
