"""Headless tests for the pygame renderer (SDL dummy drivers)."""
import os
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame  # noqa: E402
import pytest  # noqa: E402

from heartlight import Cell, Engine, Event, EventKind, Input, parse_levels  # noqa: E402
from heartlight.render import (Renderer, RomData, Sounds, TileState, atari_rgb, bcd_digits,  # noqa: E402
                               load_rom, SCREEN_W, SCREEN_H)

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope='module')
def rom() -> RomData:
    return load_rom(ROOT / 'game.bin', ROOT / 'meta.json')


@pytest.fixture(scope='module', autouse=True)
def _pygame():
    pygame.init()
    pygame.display.set_mode((64, 64))
    yield
    pygame.quit()


def test_rom_data(rom):
    assert len(rom.charset) == 1024 and rom.charset[:20] == bytes(20)
    assert rom.tile_tab[Cell.EMPTY] == 0x00
    assert rom.tile_tab[Cell.ROCK] == rom.tile_tab[Cell.ROCK_FALLING] == 0x0C
    assert rom.tile_tab[Cell.HARD_WALL] == 0x9E and rom.tile_tab[Cell.HEART] == 0x90
    assert [rom.tile_tab[c] for c in range(Cell.ANIM0, Cell.ANIM6 + 1)] == [2, 4, 6, 8, 6, 4, 2]
    assert len(rom.status) == 40 and rom.status[5:7] == b'\x1a\x1b'
    assert rom.colors == (4, 6, 14, 10, 0)


def test_palette():
    assert atari_rgb(0) == (0, 0, 0)
    assert atari_rgb(14) == (238, 238, 238)
    r, g, b = atari_rgb(0x48)
    assert not (r == g == b)


def test_bcd_digits():
    assert bcd_digits(0) == (0, 0) and bcd_digits(7) == (0, 7) and bcd_digits(42) == (4, 2)
    assert bcd_digits(255) == (9, 9) and bcd_digits(-1) == (0, 0)


def test_tile_state_hero_facing_and_walk(rom):
    t = TileState(dict(rom.tile_tab))
    assert t.hero == 0x18
    t.after_tick(Input.LEFT, 0, 5)
    assert t.hero == 0x16
    t.after_tick(Input.LEFT, 1, 5)
    assert t.hero == 0x14
    t.after_tick(Input.NONE, 2, 5)
    assert t.hero == 0x14
    t.after_tick(Input.RIGHT, 3, 5)
    assert t.hero == 0x1A
    t.after_tick(Input.UP, 4, 5)
    assert t.hero == 0x18                     # up/down keep facing, toggle walk
    t.on_room_loaded()
    assert t.hero == 0x18


def test_tile_state_exit_and_heart_blink(rom):
    t = TileState(dict(rom.tile_tab))
    assert t.exit == 0x9C and t.heart == 0x90
    t.on_room_loaded()
    assert t.exit == 0x1C
    t.after_tick(Input.NONE, 0, 3)            # closed: unchanged; heart flips on even tick
    assert t.exit == 0x1C and t.heart == 0x10
    t.after_tick(Input.NONE, 1, 3)
    assert t.heart == 0x10
    t.after_tick(Input.NONE, 2, 0)            # open, tick&4 == 0
    assert t.exit == 0x1C and t.heart == 0x90
    t.after_tick(Input.NONE, 4, 0)            # open, tick&4 != 0
    assert t.exit == 0x9C
    assert t.base_for(Cell.EXIT) == 0x9C and t.base_for(Cell.HEART_FALLING) == t.heart
    assert t.base_for(Cell.SOFT_WALL) == 0x0A


def test_status_line_digits(rom):
    r = Renderer(rom, scale=1)
    st = r.status_bytes(lives=3, room=0)
    assert st[8:10] == b'\x40\x43' and st[34:36] == b'\x40\x41'
    assert st[:8] == rom.status[:8]


def test_draw_real_room(rom):
    rooms = parse_levels((ROOT / 'levels.txt').read_text())
    e = Engine(rooms)
    tiles = TileState(dict(rom.tile_tab))
    r = Renderer(rom, scale=2)
    assert r.size == (SCREEN_W * 2, SCREEN_H * 2) == (640, 432)
    surf = pygame.Surface(r.size)
    r.draw(surf, e, tiles)
    colours = {surf.get_at((x, y))[:3] for x in range(0, 640, 7) for y in range(0, 432, 7)}
    assert len(colours) >= 3
    # a hard-wall cell (0,0 of the grid) is not background; an empty cell of room 2 is
    e2 = Engine(rooms, start_room=1)
    r.draw(surf, e2, tiles)
    gx, gy = 12 * 2 * 8 * 2 + 4, (24 + 4 * 2 * 8) * 2 + 4     # cell (12,4) of room 2 is ' '
    assert surf.get_at((gx, gy))[:3] == r.bg
    assert surf.get_at((4, 24 * 2 + 4))[:3] != r.bg


def test_sounds_build_and_play():
    s = Sounds(enabled=True)
    s.play([Event(EventKind.HEART_COLLECTED, 5), Event(EventKind.BLAST, 7, (7,))])
    s.play([])
    assert Sounds(enabled=False).play([Event(EventKind.BLAST, 7, (7,))]) is None
