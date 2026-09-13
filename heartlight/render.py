"""Stage 4: pygame renderer for the Heartlight engine.

Reproduces the original screen (DL_GAME + RENDER in game.asm): a 40x24 ANTIC
mode-4 playfield where every grid cell is a 2x2 block of characters taken from
the redefined charset inside game.bin, and a mode-5 (double height) status
line. Tile animation (exit blink, heart blink, hero facing/walk) mirrors the
TILE_EXIT / TILE_HEART / TILE_HERO bookkeeping of the original.

Sound is a stand-in: the original plays one-frame POKEY blips per event
(SND_PLAY); we synthesise short square-wave blips with the same intent.
"""
from __future__ import annotations

import array
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import pygame

from .engine import Cell, Engine, Event, EventKind, Input, ROOM_W

BIN_LOAD = 0x9014
CHARSET_ADDR = 0x9000            # CHBAS=$90; the game zeroes the first 20 bytes itself
TILE_TAB_ADDR = 0x98C9           # TILE_TAB[$20..$36]
STATUS_ADDR = 0x92A4             # STATUS_LINE, 40 bytes
STATUS_LEN = 40
SCREEN_COLS, SCREEN_ROWS = 40, 24
CHAR_PX = 8                      # a mode-4 char = 4 double-width pixels = 8 hi-res pixels, 8 scanlines
STATUS_TOP, STATUS_ROWS = 4, 16  # DL_GAME: blank 4, mode 5 (16 lines), blank 4, 24 x mode 4
GRID_TOP = STATUS_TOP + STATUS_ROWS + 4
SCREEN_W, SCREEN_H = SCREEN_COLS * CHAR_PX, GRID_TOP + SCREEN_ROWS * CHAR_PX   # 320 x 216
FRAMES_PER_TICK = 6              # WAIT_TICK: CDTMV2 = 6
FPS = 50                         # PAL

STATUS_LIVES_POS = 9             # PUT_BCD ... LDY #$09  (tens at 8, ones at 9)
STATUS_ROOM_POS = 0x23           # PUT_BCD ... LDY #$23  (tens at 34, ones at 35)


@dataclass(frozen=True)
class RomData:
    charset: bytes                       # 1024 bytes, 128 chars x 8 rows
    tile_tab: dict[int, int]             # cell code -> tile base char
    status: bytes                        # initial 40-byte status line
    colors: tuple[int, int, int, int, int]   # COLPF0..3, COLBK (registers 708..712)


def load_rom(game_bin: Path, meta_json: Path) -> RomData:
    data = game_bin.read_bytes()
    charset = bytearray(1024)
    off = BIN_LOAD - CHARSET_ADDR
    charset[off:] = data[:1024 - off]
    tt = data[TILE_TAB_ADDR - BIN_LOAD:TILE_TAB_ADDR - BIN_LOAD + 0x17]
    tile_tab = {0x20 + k: v for k, v in enumerate(tt)}
    status = data[STATUS_ADDR - BIN_LOAD:STATUS_ADDR - BIN_LOAD + STATUS_LEN]
    meta = json.loads(meta_json.read_text())
    c = meta['colors_708_712']
    return RomData(bytes(charset), tile_tab, bytes(status), (c[0], c[1], c[2], c[3], c[4]))


def atari_rgb(code: int) -> tuple[int, int, int]:
    """GTIA colour code (hue*16 + luminance) -> RGB, a common YIQ approximation."""
    hue, lum = (code >> 4) & 0xF, code & 0xF
    y = lum / 15.0
    if hue == 0:
        v = round(y * 255)
        return v, v, v
    angle = math.radians((hue - 1) * 24.0 - 33.0)
    sat = 0.30
    i, q = sat * math.cos(angle), sat * math.sin(angle)
    r = y + 0.956 * i + 0.621 * q
    g = y - 0.272 * i - 0.647 * q
    b = y - 1.106 * i + 1.703 * q
    return tuple(max(0, min(255, round(v * 255))) for v in (r, g, b))  # type: ignore[return-value]


@dataclass
class TileState:
    """The three dynamic entries of TILE_TAB and the status-line digits."""
    tile_tab: dict[int, int]
    exit: int = field(init=False)
    heart: int = field(init=False)
    hero: int = field(init=False)

    def __post_init__(self) -> None:
        self.exit = self.tile_tab[Cell.EXIT]      # $9C
        self.heart = self.tile_tab[Cell.HEART]    # $90
        self.hero = self.tile_tab[Cell.HERO]      # $18 = facing right, standing

    def on_room_loaded(self) -> None:             # LOAD_ROOM
        self.hero &= 0xFC
        self.exit &= 0x7F

    def after_tick(self, inp: Input, tick_before: int, hearts_left: int) -> None:
        if hearts_left == 0:                      # H_EXIT
            self.exit = (self.exit & 0x7F) | (0x80 if tick_before & 4 else 0)
        if inp is Input.NONE:                     # HERO_IDLE
            self.hero &= 0xFC
        else:
            if inp is Input.LEFT:                 # HERO_MOVE facing bits
                self.hero = (self.hero & 0xF3) | 0x04
            elif inp is Input.RIGHT:
                self.hero = (self.hero & 0xF3) | 0x08
            self.hero ^= 0x02                     # walk frame toggle (end of SCAN)
        if tick_before & 1 == 0:                  # heart blink (end of SCAN)
            self.heart ^= 0x80

    def base_for(self, cell: Cell) -> int:
        if cell == Cell.EXIT:
            return self.exit
        if cell in (Cell.HEART, Cell.HEART_FALLING):
            return self.heart
        if cell == Cell.HERO:
            return self.hero
        return self.tile_tab.get(int(cell), 0)


def bcd_digits(value: int) -> tuple[int, int]:
    """SHOW_LIVES / PUT_BCD: two decimal digits, capped at 99."""
    v = max(0, min(99, value))
    return v // 10, v % 10


class Renderer:
    def __init__(self, rom: RomData, scale: int = 3) -> None:
        self.rom = rom
        self.scale = scale
        self.size = (SCREEN_W * scale, SCREEN_H * scale)
        pf0, pf1, pf2, pf3, bk = (atari_rgb(c) for c in rom.colors)
        self.bg = bk
        self._palette = ((bk, pf0, pf1, pf2), (bk, pf0, pf1, pf3))   # pixel value -> colour, per bit 7
        self._cache: dict[tuple[int, bool], pygame.Surface] = {}

    def char_surface(self, code: int, double: bool = False) -> pygame.Surface:
        key = (code, double)
        surf = self._cache.get(key)
        if surf is not None:
            return surf
        s = self.scale
        h = 2 if double else 1
        surf = pygame.Surface((CHAR_PX * s, CHAR_PX * s * h))
        pal = self._palette[code >> 7]
        base = (code & 0x7F) * 8
        for row in range(8):
            byte = self.rom.charset[base + row]
            for px in range(4):
                v = (byte >> (6 - 2 * px)) & 3
                surf.fill(pal[v], (px * 2 * s, row * s * h, 2 * s, s * h))
        self._cache[key] = surf
        return surf

    def status_bytes(self, lives: int, room: int) -> bytes:
        buf = bytearray(self.rom.status)
        for pos, value in ((STATUS_LIVES_POS, lives), (STATUS_ROOM_POS, room + 1)):
            tens, ones = bcd_digits(value)
            buf[pos - 1], buf[pos] = 0x40 + tens, 0x40 + ones     # PUT_DIGIT: no colour bit
        return bytes(buf)

    def draw(self, target: pygame.Surface, engine: Engine, tiles: TileState) -> None:
        s = self.scale
        target.fill(self.bg)
        st = engine.state
        for k, code in enumerate(self.status_bytes(st.lives, st.room)):
            target.blit(self.char_surface(code, double=True), (k * CHAR_PX * s, STATUS_TOP * s))
        grid = engine.grid
        for i, cell in enumerate(grid):
            base = tiles.base_for(cell)
            x = (i % ROOM_W) * 2 * CHAR_PX * s
            y = (GRID_TOP + (i // ROOM_W) * 2 * CHAR_PX) * s
            target.blit(self.char_surface(base), (x, y))
            target.blit(self.char_surface(base | 0x01), (x + CHAR_PX * s, y))
            target.blit(self.char_surface(base | 0x20), (x, y + CHAR_PX * s))
            target.blit(self.char_surface(base | 0x21), (x + CHAR_PX * s, y + CHAR_PX * s))


class Sounds:
    """Short synthesised blips keyed by event kind; silent if the mixer is unavailable."""
    RATE = 22050
    SPEC: dict[EventKind, tuple[float, float, bool]] = {       # (Hz, seconds, noise)
        EventKind.GRASS_EATEN: (180.0, 0.03, True),
        EventKind.PUSHED: (140.0, 0.04, False),
        EventKind.ROCK_LANDED: (90.0, 0.05, False),
        EventKind.BOMB_LANDED: (90.0, 0.05, False),
        EventKind.HEART_LANDED: (300.0, 0.04, False),
        EventKind.HEART_COLLECTED: (880.0, 0.08, False),
        EventKind.BLAST: (60.0, 0.18, True),
        EventKind.HERO_DIED: (50.0, 0.30, True),
        EventKind.ROOM_COMPLETE: (660.0, 0.25, False),
        EventKind.EXTRA_LIFE: (1320.0, 0.25, False),
        EventKind.GAME_OVER: (40.0, 0.60, True),
    }

    def __init__(self, enabled: bool = True) -> None:
        self._sounds: dict[EventKind, pygame.mixer.Sound] = {}
        if not enabled:
            return
        try:
            pygame.mixer.init(frequency=self.RATE, size=-16, channels=1, buffer=512)
        except pygame.error:
            return
        for kind, (hz, secs, noise) in self.SPEC.items():
            self._sounds[kind] = self._make(hz, secs, noise)

    def _make(self, hz: float, secs: float, noise: bool) -> pygame.mixer.Sound:
        n = int(self.RATE * secs)
        rnd = random.Random(int(hz))
        period = self.RATE / hz
        samples = array.array('h')
        for k in range(n):
            env = 1.0 - k / n
            if noise:
                v = rnd.choice((-1.0, 1.0))
            else:
                v = 1.0 if (k % period) < period / 2 else -1.0
            samples.append(int(v * env * 12000))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, events: Sequence[Event]) -> None:
        if not self._sounds:
            return
        best: EventKind | None = None
        for ev in events:
            if ev.kind in self._sounds and (best is None or self.SPEC[ev.kind][1] > self.SPEC[best][1]):
                best = ev.kind             # one blip per tick, the longest wins (cf. SND_PRI)
        if best is not None:
            self._sounds[best].play()
