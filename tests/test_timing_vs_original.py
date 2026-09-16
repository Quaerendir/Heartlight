"""Run the original 6502 code (py65) and check the engine's timing constants against it."""
import sys
from pathlib import Path

import pytest

py65 = pytest.importorskip('py65')
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import verify_timing  # noqa: E402

from heartlight import DEATH_TICKS  # noqa: E402
from heartlight.engine import INITIAL_TICK  # noqa: E402
from heartlight.render import CURTAIN_FRAMES_PER_STEP, CURTAIN_ROUNDS, FRAMES_PER_TICK  # noqa: E402


def test_constants_match_the_original_code():
    tick = verify_timing.check_loader(ROOT / 'heartlight.bas')
    assert tick == INITIAL_TICK == 0x4B
    r = verify_timing.run_game(tick)
    assert r['tick_at_first_scan'] == INITIAL_TICK
    assert r['scans_in_death_wait'] == DEATH_TICKS == 11
    scans = [f for e, f in r['timeline'] if e == 'scan']
    gaps = [b - a for a, b in zip(scans, scans[1:])]
    assert gaps[0] == 1                                          # first scan of a room does not wait
    assert set(gaps[1:]) == {FRAMES_PER_TICK}                    # then one scan per 6 frames
    # title + curtain (2 phases x (25 rounds + fill) steps x 3 frames) before the first scan
    assert scans[0] == 2 * (CURTAIN_ROUNDS + 1) * CURTAIN_FRAMES_PER_STEP + 4


def test_xex_boots_like_the_basic_loaded_game(tmp_path):
    import build_xex
    xex = build_xex.build(ROOT)
    segs = build_xex.parse(xex)
    assert [(s, e) for s, e, _ in segs] == [(0x02C8, 0x02CC), (0x7000, 0x7000 + 3 + 20 + 12 * 240 - 1),
                                            (0x9014, 0x9907), (0x00D0, 0x00D0), (0x02E0, 0x02E1)]
    assert segs[2][2] == (ROOT / 'game.bin').read_bytes()
    assert segs[1][2][:3] == bytes([3, 2, 12]) and segs[1][2][3:23] == b'    JANUSZ  PELC    '
    assert segs[4][2] == b'\x60\x92'
    assert (ROOT / 'heartlight.xex').read_bytes() == xex          # committed file is current
    p = tmp_path / 'h.xex'
    p.write_bytes(xex)
    r = verify_timing.run_game(xex=p)
    assert r['tick_at_first_scan'] == INITIAL_TICK
    assert r['scans_in_death_wait'] == DEATH_TICKS
