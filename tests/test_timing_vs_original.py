"""Run the original 6502 code (py65) and check the engine's timing constants against it."""
import json
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
    assert [(s, e) for s, e, _ in segs] == [(0x02C4, 0x02C8), (0x7000, 0x7000 + 3 + 20 + 12 * 240 - 1),
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


def test_saver_layout_matches_our_xex():
    """tools/build_xex.py --saver = the file SHORTHSV.LST (TA 2/91) would write; same memory image."""
    import build_xex
    ours, saver = build_xex.build(ROOT), build_xex.build_saver(ROOT)
    segs = build_xex.parse(saver)
    n_rooms = json.loads((ROOT / 'meta.json').read_text())['rooms']
    assert [(s, e) for s, e, _ in segs] == [(0x02E0, 0x02E1), (0x02C4, 0x02C8), (0x9000, 0x98FF),
                                            (0x7000, 0x7000 + n_rooms * 240 + 23 - 1)]
    assert saver[:12] == bytes.fromhex('ffffe002e1026092c402c802')      # SHORTHSV.LST line 2010
    assert saver[17:21] == bytes.fromhex('0090ff98')                       # line 2020
    mem_a, mem_b = bytearray(65536), bytearray(65536)
    build_xex.load_into(mem_a, ours)
    build_xex.load_into(mem_b, saver)
    assert mem_a[0x7000:0x7B57] == mem_b[0x7000:0x7B57] and mem_a[0x02C4:0x02C9] == mem_b[0x02C4:0x02C9]
    assert mem_a[0x9014:0x9900] == mem_b[0x9014:0x9900] and mem_a[0x02E0:0x02E2] == mem_b[0x02E0:0x02E2]
    assert mem_a[0x9900:0x9908] == bytes(8)                                # only zero padding beyond $98FF
    assert mem_a[0xD0] == 0x4B and mem_b[0xD0] == 0                        # the saver leaves TICK alone
