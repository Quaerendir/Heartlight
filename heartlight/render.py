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
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Sequence

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
TITLE_TEXT_ADDR = 0x92CC         # 3 x 20 bytes: mode-7 "HEARTLIGHT", mode-6 author, mode-6 "AUTOR KOMNAT:"
TITLE_LAYOUT = ((0, 7), (24, 6), (64, 6), (80, 6))   # DL_TITLE: (top scanline, ANTIC mode) per text line
TEXT_COLS = 20                   # modes 6/7 are 20 chars wide, 16 hi-res pixels each
CURTAIN_ROUNDS, CURTAIN_PER_ROUND = 25, 40           # CURTAIN: LDX #$19 rounds of LDX #$28 random cells
CURTAIN_FRAMES_PER_STEP = 3      # CURTAIN_FRAME: WAIT_VBL + the two WAIT_VBLs inside SND_PLAY


@dataclass(frozen=True)
class RomData:
    charset: bytes                       # 1024 bytes, 128 chars x 8 rows
    tile_tab: dict[int, int]             # cell code -> tile base char
    status: bytes                        # initial 40-byte status line
    colors: tuple[int, int, int, int, int]   # COLPF0..3, COLBK (registers 708..712)
    title_text: bytes = b''              # 60 bytes at TITLE_TEXT_ADDR (screen codes with colour bits)


def load_rom(game_bin: Path, meta_json: Path) -> RomData:
    data = game_bin.read_bytes()
    charset = bytearray(1024)
    off = BIN_LOAD - CHARSET_ADDR
    charset[off:] = data[:1024 - off]
    tt = data[TILE_TAB_ADDR - BIN_LOAD:TILE_TAB_ADDR - BIN_LOAD + 0x17]
    tile_tab = {0x20 + k: v for k, v in enumerate(tt)}
    status = data[STATUS_ADDR - BIN_LOAD:STATUS_ADDR - BIN_LOAD + STATUS_LEN]
    title = data[TITLE_TEXT_ADDR - BIN_LOAD:TITLE_TEXT_ADDR - BIN_LOAD + 3 * TEXT_COLS]
    meta = json.loads(meta_json.read_text())
    c = meta['colors_708_712']
    return RomData(bytes(charset), tile_tab, bytes(status), (c[0], c[1], c[2], c[3], c[4]), bytes(title))


def load_os_font(path: Path) -> bytes:
    """The standard Atari charset (CHBAS=$E0 on the title screen): a 1 KB dump, or an OS ROM
    image (16 KB XL/XE: charset at $E000 = offset $2000; 10 KB 400/800 OS-B: offset $800)."""
    data = path.read_bytes()
    if len(data) == 1024:
        return data
    if len(data) == 16384:
        return data[0x2000:0x2400]
    if len(data) == 10240:
        return data[0x800:0xC00]
    raise ValueError(f'{path}: expected a 1 KB charset or a 10/16 KB OS ROM, got {len(data)} bytes')


def atascii_to_screen(ch: int) -> int:
    """TITLE_CONV: ATASCII -> screen code, keeping bit 7 (inverse video)."""
    hi, a = ch & 0x80, ch & 0x7F
    if a < 0x20:
        a += 0x40
    elif a < 0x60:
        a -= 0x20
    return a | hi


def parse_title_banner(levels_text: str) -> str:
    """The 20-char banner line 1070 of the listing, as recorded by the extractor in levels.txt."""
    m = re.search(r'^; title banner: \[(.{20})\]', levels_text, re.M)
    return m.group(1) if m else ' ' * TEXT_COLS


@dataclass(frozen=True)
class TextLine:
    """One ANTIC mode 6/7 line: 6-bit char codes and the colour register (0..3) of each."""
    chars: tuple[int, ...]
    colours: tuple[int, ...]

    @classmethod
    def from_screen_codes(cls, raw: Sequence[int]) -> 'TextLine':
        return cls(tuple(b & 0x3F for b in raw), tuple((b >> 6) & 3 for b in raw))

    @classmethod
    def from_atascii(cls, text: str) -> 'TextLine':
        return cls.from_screen_codes([atascii_to_screen(ord(c) & 0xFF) for c in text])

    def __str__(self) -> str:
        return ''.join(chr(c + 0x20) for c in self.chars)


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
        self.playfield = (pf0, pf1, pf2, pf3)
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
        st = engine.state
        self.draw_status(target, st.lives, st.room)
        self.draw_grid(target, engine.grid, tiles)

    def draw_status(self, target: pygame.Surface, lives: int, room: int) -> None:
        s = self.scale
        target.fill(self.bg)
        for k, code in enumerate(self.status_bytes(lives, room)):
            target.blit(self.char_surface(code, double=True), (k * CHAR_PX * s, STATUS_TOP * s))

    def draw_grid(self, target: pygame.Surface, grid: Sequence[int], tiles: TileState) -> None:
        s = self.scale
        for i, cell in enumerate(grid):
            base = tiles.base_for(Cell(cell))
            x = (i % ROOM_W) * 2 * CHAR_PX * s
            y = (GRID_TOP + (i // ROOM_W) * 2 * CHAR_PX) * s
            target.blit(self.char_surface(base), (x, y))
            target.blit(self.char_surface(base | 0x01), (x + CHAR_PX * s, y))
            target.blit(self.char_surface(base | 0x20), (x, y + CHAR_PX * s))
            target.blit(self.char_surface(base | 0x21), (x + CHAR_PX * s, y + CHAR_PX * s))


class TextFont:
    """Glyphs for ANTIC modes 6/7 (20 columns, double-width pixels). Pixel-exact with the
    Atari OS charset; otherwise a system monospace font stretched to the same cell."""

    def __init__(self, scale: int, os_font: bytes | None = None) -> None:
        self.scale = scale
        self.os_font = os_font
        self._sys: pygame.font.Font | None = None
        if os_font is None:
            pygame.font.init()
            self._sys = pygame.font.SysFont('dejavusansmono,liberationmono,couriernew,monospace',
                                            10 * scale, bold=True)
        self._cache: dict[tuple[int, int, tuple[int, int, int], tuple[int, int, int]], pygame.Surface] = {}

    def glyph(self, code6: int, mode: int, fg: tuple[int, int, int], bg: tuple[int, int, int]) -> pygame.Surface:
        key = (code6, mode, fg, bg)
        surf = self._cache.get(key)
        if surf is not None:
            return surf
        s = self.scale
        h = 2 if mode == 7 else 1
        w, hh = 2 * CHAR_PX * s, CHAR_PX * s * h
        surf = pygame.Surface((w, hh))
        surf.fill(bg)
        if self.os_font is not None:
            base = (code6 & 0x3F) * 8
            for row in range(8):
                byte = self.os_font[base + row]
                for px in range(8):
                    if byte & (0x80 >> px):
                        surf.fill(fg, (px * 2 * s, row * s * h, 2 * s, s * h))
        elif self._sys is not None and code6 != 0:
            text = self._sys.render(chr(code6 + 0x20), False, fg, bg)
            box = pygame.transform.scale(text, (int(w * 0.8), int(hh * 0.9)))
            surf.blit(box, ((w - box.get_width()) // 2, (hh - box.get_height()) // 2))
        self._cache[key] = surf
        return surf


class TitleScreen:
    """DL_TITLE: HEARTLIGHT / AUTOR: JANUSZ PELC / AUTOR KOMNAT: / <banner from the level data>."""

    def __init__(self, rom: RomData, banner: str, renderer: Renderer, font: TextFont) -> None:
        raw = rom.title_text
        self.lines = [TextLine.from_screen_codes(raw[k:k + TEXT_COLS]) for k in range(0, 3 * TEXT_COLS, TEXT_COLS)]
        self.lines.append(TextLine.from_atascii(banner.ljust(TEXT_COLS)[:TEXT_COLS]))
        self.renderer = renderer
        self.font = font

    def draw(self, target: pygame.Surface) -> None:
        r, s = self.renderer, self.renderer.scale
        target.fill(r.bg)
        for (top, mode), line in zip(TITLE_LAYOUT, self.lines):
            for k, (ch, col) in enumerate(zip(line.chars, line.colours)):
                target.blit(self.font.glyph(ch, mode, r.playfield[col], r.bg), (k * 2 * CHAR_PX * s, top * s))


class Curtain:
    """LOAD_ROOM's reveal: 25 frames of 40 random cells turning into soft wall, a full fill,
    then the same again with the real room. `cells` is what to draw after each step()."""

    def __init__(self, start: Sequence[int], target: Sequence[int], rnd: random.Random | None = None) -> None:
        self.cells: list[int] = [int(c) for c in start]
        self._target = [int(c) for c in target]
        self._rnd = rnd or random.Random()
        self._frames = self._gen()
        self.running = True

    def _gen(self) -> Iterator[None]:
        n = len(self.cells)
        for phase in range(2):                                   # CURTAIN_MODE $80, then real cells
            for _ in range(CURTAIN_ROUNDS):
                for _ in range(CURTAIN_PER_ROUND):
                    i = self._rnd.randrange(n)
                    self.cells[i] = Cell.SOFT_WALL if phase == 0 else self._target[i]
                yield
            for i in range(n):                                   # CU_FILL
                self.cells[i] = Cell.SOFT_WALL if phase == 0 else self._target[i]
            yield

    def step(self) -> bool:
        try:
            next(self._frames)
            return True
        except StopIteration:
            self.running = False
            return False


# ---------------------------------------------------------------- sound (SND_REQ / SND_PLAY)
POKEY_CLOCK = 1_773_447          # PAL POKEY input clock (Hz)
POKEY_BASE_DIV = 28              # AUDCTL=0: channel clocked at 64 kHz (1.77 MHz / 28)
FRAME_SECONDS = 1 / 50           # a blip lasts exactly one PAL frame (WAIT_VBL .. WAIT_VBL)
SND_F = (0x00, 0x04, None, 0x10)         # AUDF by priority-1; index 2 is written with (RANDOM & 15) + 8
SND_C = (0x81, 0x04, 0xA4, 0x00)         # AUDC by priority-1; priority >= 4 uses (priority-1) | SND_C[3]
SOUND_PRIORITY: dict[EventKind, int] = { # every JSR SND_REQ site in game.asm
    EventKind.GRASS_EATEN: 1, EventKind.PUSHED: 1,
    EventKind.ROCK_LANDED: 2, EventKind.ROCK_ROLLED: 2, EventKind.ROCK_HIT: 2,
    EventKind.BOMB_LANDED: 2, EventKind.BOMB_HIT: 2,
    EventKind.HEART_COLLECTED: 3, EventKind.HEART_LANDED: 3, EventKind.HEART_ROLLED: 3, EventKind.HEART_HIT: 3,
}
BLAST_FRAME_PRIORITY = 4         # SC_CELL: SEC; SBC #$30; ADC #$03  ->  frame + 4
CURTAIN_PRIORITY = 3


def sound_priority(events: Sequence[Event]) -> int:
    """SND_REQ keeps the maximum priority requested during a tick; 0 = silence."""
    best = 0
    for ev in events:
        if ev.kind is EventKind.BLAST_FRAME:
            best = max(best, ev.value + BLAST_FRAME_PRIORITY)
        else:
            best = max(best, SOUND_PRIORITY.get(ev.kind, 0))
    return best


def sound_registers(priority: int, rnd: random.Random) -> tuple[int, int]:
    """SND_PLAY: (AUDF1, AUDC1) for a priority >= 1."""
    y = priority - 1
    if y >= 3:
        return SND_F[3], (y | SND_C[3]) & 0xFF
    audf = SND_F[y]
    if audf is None:
        audf = (rnd.randrange(256) & 0x0F) + 0x08          # RANDOM AND #$0F, ADC #$08 (carry clear)
    return audf, SND_C[y]


def _lfsr(bits: int, tap: int) -> bytes:
    """Output of the maximal-length shift register x^bits + x^tap + 1 (period 2**bits - 1):
    a[n+bits] = a[n] ^ a[n+tap], register shifted right, output at bit 0."""
    reg, out = (1 << bits) - 1, bytearray()
    for _ in range((1 << bits) - 1):
        out.append(reg & 1)
        bit = (reg ^ (reg >> tap)) & 1
        reg = (reg >> 1) | (bit << (bits - 1))
    return bytes(out)


class Pokey:
    """One POKEY audio channel under AUDCTL=0, rendered to 16-bit mono PCM.

    Polynomial counters run at the 1.77 MHz clock; the channel divider runs at 64 kHz and
    fires every AUDF+1 ticks. AUDC: bit 7 = skip the 5-bit poly gate, bit 6 = 4-bit poly
    instead of 17-bit, bit 5 = pure tone, bits 0-3 = volume.
    """
    POLY4 = _lfsr(4, 3)               # x^4 + x^3 + 1
    POLY5 = _lfsr(5, 3)               # x^5 + x^3 + 1
    POLY17: bytes | None = None      # built on first use (131071 steps)

    def __init__(self, sample_rate: int = 44100, amplitude: int = 20000) -> None:
        self.sample_rate = sample_rate
        self.amplitude = amplitude
        if Pokey.POLY17 is None:
            Pokey.POLY17 = _lfsr(17, 12)          # x^17 + x^12 + 1

    def render(self, audf: int, audc: int, seconds: float = FRAME_SECONDS) -> array.array[int]:
        base_hz = POKEY_CLOCK / POKEY_BASE_DIV
        n_base = int(round(base_hz * seconds))
        volume = audc & 0x0F
        pure, poly4, skip5 = audc & 0x20, audc & 0x40, audc & 0x80
        p4, p5, p17 = Pokey.POLY4, Pokey.POLY5, Pokey.POLY17 or b''
        counter, out, clock = audf, 0, 0
        levels = bytearray(n_base)
        for t in range(n_base):
            clock += POKEY_BASE_DIV
            if counter == 0:
                counter = audf
                if skip5 or p5[clock % 31]:
                    if pure:
                        out ^= 1
                    elif poly4:
                        out = p4[clock % 15]
                    else:
                        out = p17[clock % 131071]
            else:
                counter -= 1
            levels[t] = out
        # box-filter resample 64 kHz -> sample_rate, centred, scaled by volume
        n_out = int(round(self.sample_rate * seconds))
        samples = array.array('h')
        gain = self.amplitude * volume / 15
        for k in range(n_out):
            a, b = k * n_base // n_out, max(k * n_base // n_out + 1, (k + 1) * n_base // n_out)
            mean = sum(levels[a:b]) / (b - a)
            samples.append(int((mean * 2 - 1) * gain))
        return samples


class Sounds:
    """SND_REQ/SND_PLAY: at most one blip per tick, the highest priority wins, one frame long."""
    RATE = 44100

    def __init__(self, enabled: bool = True, rnd: random.Random | None = None) -> None:
        self.enabled = False
        self.rnd = rnd or random.Random()
        self.last: tuple[int, int] | None = None      # (AUDF, AUDC) of the last blip, for tests
        self._cache: dict[tuple[int, int], pygame.mixer.Sound] = {}
        self._pokey = Pokey(self.RATE)
        if not enabled:
            return
        try:
            pygame.mixer.init(frequency=self.RATE, size=-16, channels=1, buffer=256)
        except pygame.error:
            return
        self.enabled = True

    def request(self, priority: int) -> None:
        if priority <= 0:
            return
        regs = sound_registers(priority, self.rnd)
        self.last = regs
        if not self.enabled:
            return
        snd = self._cache.get(regs)
        if snd is None:
            snd = pygame.mixer.Sound(buffer=self._pokey.render(*regs).tobytes())
            self._cache[regs] = snd
        snd.play()

    def play(self, events: Sequence[Event]) -> None:
        self.request(sound_priority(events))

    def curtain_blip(self) -> None:
        """CURTAIN_FRAME: LDA #$03; JSR SND_REQ; JSR SND_PLAY every frame."""
        self.request(CURTAIN_PRIORITY)
