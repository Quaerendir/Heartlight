"""Headless tests for the pygame renderer (SDL dummy drivers)."""
import os
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame  # noqa: E402
import pytest  # noqa: E402

from heartlight import Cell, Engine, Event, EventKind, Input, parse_levels  # noqa: E402
from heartlight.render import (Renderer, RomData, Sounds, TileState, atari_rgb, bcd_digits,  # noqa: E402
                               load_rom, SCREEN_W, SCREEN_H, Pokey, POKEY_CLOCK, POKEY_BASE_DIV,
                               sound_priority, sound_registers)

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


def test_sound_priority_is_max_of_requests():
    assert sound_priority([]) == 0
    assert sound_priority([Event(EventKind.GRASS_EATEN, 1), Event(EventKind.PUSHED, 2)]) == 1
    assert sound_priority([Event(EventKind.ROCK_LANDED, 1), Event(EventKind.HEART_COLLECTED, 2)]) == 3
    assert sound_priority([Event(EventKind.BLAST_FRAME, 1, value=0)]) == 4
    assert sound_priority([Event(EventKind.BLAST_FRAME, 1, value=6), Event(EventKind.BLAST_FRAME, 2, value=2)]) == 10
    assert sound_priority([Event(EventKind.BLAST, 1, (1,)), Event(EventKind.ROOM_COMPLETE, 1)]) == 0


def test_sound_registers_follow_snd_play():
    rnd = random.Random(1)
    assert sound_registers(1, rnd) == (0x00, 0x81)
    assert sound_registers(2, rnd) == (0x04, 0x04)
    for _ in range(50):
        audf, audc = sound_registers(3, rnd)
        assert 8 <= audf <= 23 and audc == 0xA4
    assert sound_registers(4, rnd) == (0x10, 0x03)
    assert sound_registers(10, rnd) == (0x10, 0x09)


def test_pokey_pure_tone_frequency():
    pk = Pokey(44100)
    audf = 23
    samples = pk.render(audf, 0xA4, seconds=0.1)
    assert len(samples) == 4410
    crossings = sum(1 for a, b in zip(samples, samples[1:]) if (a < 0) != (b < 0))
    expected = 2 * (POKEY_CLOCK / POKEY_BASE_DIV) / (2 * (audf + 1)) * 0.1     # 2 crossings per period
    assert abs(crossings - expected) <= 3
    assert max(samples) > 4000 and min(samples) < -4000                        # volume 4 of 15


def test_pokey_noise_and_volume():
    pk = Pokey(44100)
    one_frame = pk.render(0x00, 0x81)
    assert len(one_frame) == 882                                               # 20 ms
    assert max(abs(v) for v in one_frame) <= 20000 * 1 / 15 + 1                # volume 1
    noise = pk.render(0x10, 0x09, seconds=0.1)                                # 372 pulses in 0.1 s
    changes = sum(1 for a, b in zip(noise, noise[1:]) if a != b)
    assert 60 < changes < 372                                                  # irregular, gated
    tone = pk.render(0x10, 0xA9, seconds=0.1)
    assert sum(1 for a, b in zip(tone, tone[1:]) if a != b) > 300             # pure tone: every pulse
    gated = pk.render(0x04, 0x04, seconds=0.1)
    assert sum(1 for a, b in zip(gated, gated[1:]) if a != b) > 100
    assert max(pk.render(0x10, 0x00)) == 0                                     # volume 0 is silence


def test_sounds_play_uses_max_priority_and_one_frame():
    s = Sounds(enabled=True, rnd=random.Random(3))
    s.play([Event(EventKind.GRASS_EATEN, 1), Event(EventKind.ROCK_LANDED, 2)])
    assert s.last == (0x04, 0x04)
    s.play([])
    assert s.last == (0x04, 0x04)                                              # silence leaves it
    s.curtain_blip()
    assert s.last is not None and s.last[1] == 0xA4
    s.play([Event(EventKind.BLAST_FRAME, 5, value=6)])
    assert s.last == (0x10, 0x09)
    off = Sounds(enabled=False)
    off.play([Event(EventKind.HEART_COLLECTED, 1)])
    assert off.last == (None, None) or off.last is not None and off.last[1] == 0xA4



# ---------------------------------------------------------------- title screen and curtain
from heartlight.render import (Curtain, TextFont, TextLine, TitleScreen, atascii_to_screen,  # noqa: E402
                               load_os_font, parse_title_banner, CURTAIN_ROUNDS)
import random  # noqa: E402


def test_atascii_to_screen_matches_title_conv():
    assert atascii_to_screen(ord(' ')) == 0x00
    assert atascii_to_screen(ord('J')) == 0x2A
    assert atascii_to_screen(ord('a')) == 0x61
    assert atascii_to_screen(0x01) == 0x41            # control chars -> $40..
    assert atascii_to_screen(0xCA) == 0xAA            # inverse video keeps bit 7


def test_title_text_decoded_from_game_bin(rom):
    lines = [TextLine.from_screen_codes(rom.title_text[k:k + 20]) for k in (0, 20, 40)]
    assert [str(ln).strip() for ln in lines] == ['HEARTLIGHT', 'AUTOR: JANUSZ PELC', 'AUTOR KOMNAT:']
    def text_colours(ln: TextLine) -> set[int]:
        return {col for ch, col in zip(ln.chars, ln.colours) if ch != 0}
    assert [text_colours(ln) for ln in lines] == [{2}, {1}, {3}]


def test_title_banner_from_levels_txt():
    banner = parse_title_banner((ROOT / 'levels.txt').read_text())
    assert banner == '    JANUSZ  PELC    '
    line = TextLine.from_atascii(banner)
    assert str(line) == banner and set(line.colours) == {0}
    assert parse_title_banner('no banner here') == ' ' * 20


def test_title_screen_draws_with_fallback_font(rom):
    r = Renderer(rom, scale=2)
    t = TitleScreen(rom, '    JANUSZ  PELC    ', r, TextFont(2))
    surf = pygame.Surface(r.size)
    t.draw(surf)
    band = {surf.get_at((x, y))[:3] for x in range(160, 480, 3) for y in range(0, 32, 2)}
    assert len(band) >= 2 and r.bg in band            # "HEARTLIGHT" band has text pixels


def test_title_screen_with_os_font(rom, tmp_path):
    font = bytearray(1024)
    font[0x28 * 8:0x28 * 8 + 8] = b'\xff' * 8         # 'H' as a solid block
    p = tmp_path / 'font.bin'
    p.write_bytes(font)
    assert load_os_font(p) == bytes(font)
    rom16 = tmp_path / 'os.rom'
    rom16.write_bytes(bytes(0x2000) + bytes(font) + bytes(16384 - 0x2400))
    assert load_os_font(rom16) == bytes(font)
    (tmp_path / 'bad.bin').write_bytes(b'\0' * 100)
    with pytest.raises(ValueError):
        load_os_font(tmp_path / 'bad.bin')
    r = Renderer(rom, scale=1)
    t = TitleScreen(rom, ' ' * 20, r, TextFont(1, bytes(font)))
    surf = pygame.Surface(r.size)
    t.draw(surf)
    assert surf.get_at((5 * 16 + 1, 1))[:3] == r.playfield[2]      # first 'H' of HEARTLIGHT, PF2
    assert surf.get_at((6 * 16 + 1, 1))[:3] == r.bg                # 'E' is blank in the fake font


def test_curtain_sequence():
    start = [Cell.EMPTY] * 240
    target = list(Engine(parse_levels((ROOT / 'levels.txt').read_text())).grid)
    c = Curtain(start, target, random.Random(7))
    for _ in range(CURTAIN_ROUNDS):
        assert c.step()
        assert set(c.cells) <= {Cell.EMPTY, Cell.SOFT_WALL}
    assert Cell.SOFT_WALL in c.cells
    assert c.step() and c.cells == [Cell.SOFT_WALL] * 240
    for _ in range(CURTAIN_ROUNDS):
        assert c.step()
    assert c.cells != target and all(a == b or a == Cell.SOFT_WALL for a, b in zip(c.cells, target))
    assert c.step() and c.cells == target
    assert not c.step() and not c.running
    assert Curtain(start, target, random.Random(7)).cells is not start


def test_package_data_matches_pipeline_outputs():
    """heartlight/data/ ships copies of the stage-1 outputs; they must not drift."""
    from heartlight.play import DATA_DIR
    for name in ('game.bin', 'meta.json', 'levels.txt'):
        assert (DATA_DIR / name).read_bytes() == (ROOT / name).read_bytes(), name
