#!/usr/bin/env python3
"""Confirm the two [EMU] constants of SPEC.md by running the original 6502 code in py65.

1. INITIAL_TICK: run the listing's hex-line decoder (loader.bin, RHEX at $0603) over every
   hex DATA line exactly as BASIC line 130 does and read $D0 (TICK) afterwards.
2. DEATH_TICKS: run game.bin from PLAY with a minimal OS model (VBI every PAL frame:
   RTCLOK++, CDTMV2/CDTMV3 decrement while non-zero; RANDOM; CONSOL/SKSTAT/TRIG/PORTA
   idle), press START, wait for the room, press ESC and count SCAN calls between
   `STA CDTMV3` ($933F) and `DEC LIVES` ($934A).

Usage: python3 tools/verify_timing.py [heartlight.bas] [--xex]   (--xex: boot heartlight.xex instead)
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from heartlight_extract import HEXLINE, data_payload, logical_lines  # noqa: E402

P6, RHEX, LOAD_ADDR, PLAY = 0x0600, 0x0603, 0x9014, 0x9260
CAV, TITLE_ADDR, ROOMS_ADDR = 0x7000, 0x7003, 0x7017
RTCLOK, CDTMV2, CDTMV3, CH = 0x0014, 0x021C, 0x021E, 0x02FC
CONSOL, TRIG0, TRIG1, SKSTAT, RANDOM, PORTA = 0xD01F, 0xD010, 0xD011, 0xD20F, 0xD21A, 0xD300
SCAN, STA_CDTMV3, DEC_LIVES, WAIT_VBL_LOOP, WAIT_TICK_LOOP = 0x9678, 0x933F, 0x934A, 0x980E, 0x9717
MAIN_LOOP_KEYCHECK = 0x930E
PAL_FRAME_CYCLES = 312 * 114


def run_until(mpu: MPU, stop: int, limit: int = 5_000_000) -> None:
    for _ in range(limit):
        mpu.step()
        if mpu.pc == stop:
            return
    raise RuntimeError(f'did not reach ${stop:04X}')


def check_loader(bas: Path) -> int:
    mpu = MPU()
    mem = mpu.memory
    for i, b in enumerate((ROOT / 'loader.bin').read_bytes()):
        mem[P6 + i] = b
    hex_lines = [p for no, body in logical_lines(bas.read_text(encoding='latin-1'))
                 if (p := data_payload(body)) is not None and no >= 10000 and HEXLINE.match(p)]
    addr, string_at, sentinel = LOAD_ADDR, 0x0500, 0xFFF0
    mem[sentinel] = 0x00                                   # BRK, never reached: we stop on pc
    for line in hex_lines:
        for i, ch in enumerate(line.encode('ascii')):
            mem[string_at + i] = ch
        # BASIC's USR(RHEX, ADR(A$), A): the routine PLAs count, ADR hi, ADR lo, A hi, A lo
        mpu.sp = 0xFF
        for byte in ((sentinel - 1) >> 8, (sentinel - 1) & 0xFF,          # return address
                     addr & 0xFF, addr >> 8, string_at & 0xFF, string_at >> 8, 2):
            mem[0x100 + mpu.sp] = byte
            mpu.sp -= 1
        mpu.pc = RHEX
        run_until(mpu, sentinel)
        addr += 12
    game = (ROOT / 'game.bin').read_bytes()
    decoded = bytes(mem[LOAD_ADDR:LOAD_ADDR + len(game)])
    assert decoded == game, 'loader run does not reproduce game.bin'
    assert mem[0x0000] == 0, 'loader flagged a checksum error'
    return mem[0x00D0]


def run_game(initial_tick: int | None = None, xex: Path | None = None) -> dict[str, int]:
    """Run from PLAY. Either lay the memory out by hand (as the BASIC loader does) with the
    given initial TICK, or load a heartlight.xex like DOS would and start at its RUNAD."""
    mem = ObservableMemory()
    rnd = random.Random(1990)
    state = {'console': 0x06, 'frames': 0}                  # START pressed (bit 0 low)
    mem.subscribe_to_read([RANDOM], lambda a: rnd.randrange(256))
    mem.subscribe_to_read([CONSOL], lambda a: state['console'])
    mem.subscribe_to_read([TRIG0, TRIG1], lambda a: 1)
    mem.subscribe_to_read([SKSTAT], lambda a: 0xFF)
    mem.subscribe_to_read([PORTA], lambda a: 0xFF)
    mpu = MPU(memory=mem)
    mem[CH] = 0xFF
    if xex is not None:
        from build_xex import load_into
        mpu.pc = load_into(mem, xex.read_bytes())
    else:
        for i, b in enumerate((ROOT / 'game.bin').read_bytes()):
            mem[LOAD_ADDR + i] = b
        meta = json.loads((ROOT / 'meta.json').read_text())
        mem[CAV], mem[CAV + 1], mem[CAV + 2] = meta['lives'], meta['extra'], meta['rooms']
        text = (ROOT / 'levels.txt').read_text()
        banner = re.search(r'^; title banner: \[(.{20})\]', text, re.M).group(1)     # type: ignore[union-attr]
        for i, ch in enumerate(banner):
            mem[TITLE_ADDR + i] = ord(ch)
        rows = [ln for ln in text.splitlines() if len(ln) == 20 and not ln.startswith(';')]
        for i, ch in enumerate(''.join(rows)):
            mem[ROOMS_ADDR + i] = ord(ch)
        mem[0x00D0] = 0 if initial_tick is None else initial_tick
        mpu.pc = PLAY

    def vbi() -> None:
        state['frames'] += 1
        mem[RTCLOK] = (mem[RTCLOK] + 1) & 0xFF
        for t in (CDTMV2, CDTMV3):
            v = mem[t] | (mem[t + 1] << 8)
            if v:
                v -= 1
                mem[t], mem[t + 1] = v & 0xFF, v >> 8

    next_vbi = PAL_FRAME_CYCLES
    scans_total = scans_in_wait = 0
    in_wait = esc_sent = False
    tick_at_first_scan = tick_at_death = frames_at_wait = None
    room_scans_before_esc = 3
    timeline: list[tuple[str, int]] = []
    for _ in range(60_000_000):
        pc = mpu.pc
        if pc in (WAIT_VBL_LOOP, WAIT_TICK_LOOP):           # spinning on a timer: jump to the next VBI,
            mpu.processorCycles = max(mpu.processorCycles, next_vbi)   # which fires before the next read
            vbi()
            next_vbi += PAL_FRAME_CYCLES
        mpu.step()
        while mpu.processorCycles >= next_vbi:
            vbi()
            next_vbi += PAL_FRAME_CYCLES
        pc = mpu.pc
        if pc == SCAN:
            scans_total += 1
            timeline.append(('scan', state['frames']))
            if tick_at_first_scan is None:
                tick_at_first_scan = mem[0x00D0]
                state['console'] = 0x07                     # START released
            if in_wait:
                scans_in_wait += 1
        elif pc == MAIN_LOOP_KEYCHECK and not esc_sent:
            room_scans_before_esc -= 1
            if room_scans_before_esc == 0:
                mem[CH] = 0x1C                              # ESC
                esc_sent = True
                timeline.append(('esc', state['frames']))
        elif pc == STA_CDTMV3 and not in_wait:              # about to execute STA CDTMV3 (once)
            in_wait, frames_at_wait, tick_at_death = True, state['frames'], mem[0x00D0]
            timeline.append(('cdtmv3=64', state['frames']))
        elif pc == DEC_LIVES:
            timeline.append(('dec_lives', state['frames']))
            return {'scans_in_death_wait': scans_in_wait, 'frames_in_death_wait': state['frames'] - frames_at_wait,
                    'tick_at_first_scan': tick_at_first_scan, 'tick_at_death': tick_at_death,
                    'scans_total': scans_total, 'frames_total': state['frames'], 'timeline': timeline}
    raise RuntimeError('DEC LIVES never reached')


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    bas = Path(args[0]) if args else ROOT / 'heartlight.bas'
    tick = check_loader(bas)
    print(f'loader: all hex lines decoded through RHEX, $D0 (TICK) at PLAY = ${tick:02X} ({tick}, '
          f'{"odd" if tick & 1 else "even"})')
    xex = ROOT / 'heartlight.xex'
    r = run_game(tick, xex=xex if xex.exists() and '--xex' in sys.argv else None)
    print(f'game ({"heartlight.xex" if "--xex" in sys.argv else "BASIC-loader layout"}): '
          f'TICK seen by the first SCAN = ${r["tick_at_first_scan"]:02X}; '
          f'{r["scans_total"]} scans in {r["frames_total"]} frames before DEC LIVES')
    print(f'death wait: {r["scans_in_death_wait"]} SCAN calls over {r["frames_in_death_wait"]} frames '
          f'(CDTMV3 = 64) -> DEATH_TICKS = {r["scans_in_death_wait"]}')
    print('timeline (event @ frame):', ' '.join(f'{e}@{f}' for e, f in r['timeline']))


if __name__ == '__main__':
    main()
