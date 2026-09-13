"""Heartlight engine -- a literal re-implementation of the 6502 scan in game.asm.

Every routine here mirrors a label in game.asm (named in the docstrings). The
grid is scanned once per tick in reading order with in-place writes and a
per-cell `moved` flag, exactly like the original; do not "optimise" that into a
collect-then-apply pass, several behaviours depend on same-tick propagation.
Stdlib only, deterministic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Sequence

ROOM_W, ROOM_H = 20, 12
ROOM_CELLS = ROOM_W * ROOM_H

# DEATH_WAIT: CDTMV3 = 64 frames; scans end every 6 frames, so the 11th scan is the one that
# finds the timer at zero (tools/verify_timing.py runs the original code to confirm this).
DEATH_TICKS = 11
# TICK ($D0) is never initialised by the game. Under BASIC $CB-$D1 are the user's; the
# listing's hex-line decoder (loader.bin, RHEX) uses $D0 as its checksum accumulator, so at
# PLAY it still holds the checksum byte of the last hex line (11930): $4B. Odd, hence the
# first tick of a freshly loaded game cannot push. Confirmed by tools/verify_timing.py.
INITIAL_TICK = 0x4B


class Input(Enum):
    NONE = -1
    LEFT = 0
    RIGHT = 1
    UP = 2
    DOWN = 3


class Cell(IntEnum):
    """Cell codes. Values are the original ATASCII codes stored in GRID ($9EC0)."""
    EMPTY = 0x20
    EXIT = 0x21
    BOMB_FALLING = 0x22
    SOFT_WALL = 0x23
    HEART = 0x24
    HARD_WALL = 0x25
    BOMB = 0x26
    ROCK = 0x27
    ROCK_FALLING = 0x28
    HEART_FALLING = 0x29
    HERO = 0x2A
    BLAST = 0x2B
    COMMA = 0x2C          # unused by the levels; solid, no handler
    BOMB_WAKING = 0x2D
    GRASS = 0x2E
    ROCK_WAKING = 0x2F
    ANIM0 = 0x30
    ANIM1 = 0x31
    ANIM2 = 0x32
    ANIM3 = 0x33
    ANIM4 = 0x34
    ANIM5 = 0x35
    ANIM6 = 0x36


class EventKind(Enum):
    HEART_COLLECTED = 'heart_collected'
    GRASS_EATEN = 'grass_eaten'
    PUSHED = 'pushed'
    ROCK_LANDED = 'rock_landed'
    ROCK_ROLLED = 'rock_rolled'          # falling rock deflected diagonally (LAND_SOUND fires too)
    ROCK_HIT = 'rock_hit'                # falling rock came down on a hero or a bomb (HIT_DETONATE)
    HEART_LANDED = 'heart_landed'
    HEART_ROLLED = 'heart_rolled'
    HEART_HIT = 'heart_hit'
    BOMB_LANDED = 'bomb_landed'          # soft landing on grass
    BOMB_HIT = 'bomb_hit'                # falling bomb blocked by anything else: explodes (or hero does)
    BLAST = 'blast'
    BLAST_FRAME = 'blast_frame'          # an animation cell advanced; value = frame it had (0..6)
    HERO_DIED = 'hero_died'
    ROOM_COMPLETE = 'room_complete'
    ROOM_LOADED = 'room_loaded'
    EXTRA_LIFE = 'extra_life'
    GAME_OVER = 'game_over'


@dataclass(frozen=True)
class Event:
    kind: EventKind
    cell: int | None = None                 # grid index, when meaningful
    cells: tuple[int, ...] = ()             # BLAST: every cell written by the blast
    value: int = 0                          # BLAST_FRAME: the frame number before advancing


FELL, ROLLED, LANDED = 0, 1, 2              # _move_fall results


class Status(Enum):
    PLAYING = 'playing'
    DYING = 'dying'          # death sequence: ticking DEATH_TICKS more times, input ignored
    GAME_OVER = 'game_over'


@dataclass(frozen=True)
class GameState:
    hearts_left: int
    lives: int
    room: int
    tick: int
    status: Status
    extra_counter: int
    room_done: bool


# Direction tables (DX_TAB / DY_TAB / DIDX_TAB). Index = Input.value for the four moves.
L, R, U, D, DL, DR = range(6)
_DX = (-1, 1, 0, 0, -1, 1)
_DY = (0, 0, -1, 1, 1, 1)
_DIDX = (-1, 1, -ROOM_W, ROOM_W, ROOM_W - 1, ROOM_W + 1)
OUT = -1                     # probe result for a cell outside the grid


def parse_levels(text: str) -> list[str]:
    """levels.txt -> list of 240-char room strings (rows concatenated)."""
    rooms: list[str] = []
    lines = [ln.rstrip('\n') for ln in text.splitlines()]
    i = 0
    while i < len(lines):
        m = re.match(r'\[room (\d+)\]\s*$', lines[i])
        if not m:
            i += 1
            continue
        rows = lines[i + 1:i + 1 + ROOM_H]
        if len(rows) != ROOM_H or any(len(r) != ROOM_W for r in rows):
            raise ValueError(f'room {m.group(1)}: expected {ROOM_H} rows of {ROOM_W} chars')
        rooms.append(''.join(rows))
        i += 1 + ROOM_H
    return rooms


def _normalize_room(room: str) -> str:
    flat = room.replace('\n', '') if '\n' in room else room
    if len(flat) != ROOM_CELLS:
        raise ValueError(f'room must be {ROOM_H}x{ROOM_W} = {ROOM_CELLS} chars, got {len(flat)}')
    return flat


class Engine:
    """One instance = one game (title -> rooms -> game over)."""

    def __init__(self, rooms: Sequence[str], *, lives: int = 3, extra: int = 2,
                 start_room: int = 0, initial_tick: int = INITIAL_TICK) -> None:
        if not rooms:
            raise ValueError('need at least one room')
        self._rooms = [_normalize_room(r) for r in rooms]
        if not 0 <= start_room < len(self._rooms):
            raise ValueError(f'start_room {start_room} out of range')
        self._lives_param = lives
        self._extra_param = extra
        self.lives = lives                       # TITLE_INIT
        self.extra_counter = extra
        self.room = start_room
        self.tick_counter = initial_tick & 0xFF   # TICK survives game over in the original: pass it on
        self.hearts_left = 0
        self.room_done = False
        self.status = Status.PLAYING
        self._death_ticks = 0
        self._pending_load = False
        self._grid: list[int] = [Cell.EMPTY] * ROOM_CELLS
        self._moved = bytearray(ROOM_CELLS)
        self._events: list[Event] = []
        self._load_room()

    # ----------------------------------------------------------------- public
    @property
    def grid(self) -> Sequence[Cell]:
        return tuple(Cell(c) for c in self._grid)

    @property
    def state(self) -> GameState:
        return GameState(self.hearts_left, self.lives, self.room, self.tick_counter,
                         self.status, self.extra_counter, self.room_done)

    def tick(self, inp: Input) -> list[Event]:
        """One scan of the grid plus the between-scan bookkeeping of MAIN_LOOP."""
        self._events = []
        if self.status is Status.GAME_OVER:
            return []
        if self._pending_load:                   # ROOM_START (unless the front end drained it)
            self._pending_load = False
            self._load_room()
        if self.status is Status.DYING:          # DEATH_WAIT: keep ticking, no input
            self._scan(Input.NONE)
            self._death_ticks -= 1
            if self._death_ticks == 0:
                self.lives -= 1
                if self.lives < 0:
                    self.status = Status.GAME_OVER
                    self._emit(EventKind.GAME_OVER)
                else:
                    self.status = Status.PLAYING
                    self._pending_load = True    # same room, pristine
            return self._events
        self._scan(inp)
        if self.room_done:                       # ROOM_DONE
            self.room += 1
            if self.room >= len(self._rooms):
                self.room = 0                    # the game never ends
            self.extra_counter -= 1
            if self.extra_counter == 0:
                self.lives = min(self.lives + 1, 255)
                self.extra_counter = self._extra_param
                self._emit(EventKind.EXTRA_LIFE)
            self._pending_load = True
        elif Cell.HERO not in self._grid:        # COUNT_CELLS('*') == 0
            self.status = Status.DYING
            self._death_ticks = DEATH_TICKS
            self._emit(EventKind.HERO_DIED)
        return self._events

    @property
    def load_pending(self) -> bool:
        """True between a room change (win/death) and the load that the next tick performs."""
        return self._pending_load

    def load_room(self) -> list[Event]:
        """Perform a pending load now, without scanning. Lets a renderer show the curtain
        (LOAD_ROOM) on the freshly loaded grid before the first tick of the room."""
        self._events = []
        if self._pending_load:
            self._pending_load = False
            self._load_room()
        return self._events

    def abort_room(self) -> list[Event]:
        """ESC in the original (HERO_DEAD): every hero becomes a blast, then the death sequence."""
        self._events = []
        if self.status is not Status.PLAYING or self._pending_load:
            return []
        for i, c in enumerate(self._grid):
            if c == Cell.HERO:
                self._grid[i] = Cell.BLAST
        self.status = Status.DYING
        self._death_ticks = DEATH_TICKS
        self._emit(EventKind.HERO_DIED)
        return self._events

    # ------------------------------------------------------------- internals
    def _emit(self, kind: EventKind, cell: int | None = None, cells: tuple[int, ...] = (),
              value: int = 0) -> None:
        self._events.append(Event(kind, cell, cells, value))

    def _load_room(self) -> None:
        """LOAD_ROOM / PUT_CELL: chars $20..$2F verbatim, anything else is a rock."""
        src = self._rooms[self.room]
        for i, ch in enumerate(src):
            code = ord(ch)
            self._grid[i] = code if 0x20 <= code <= 0x2F else Cell.ROCK
        self._moved[:] = bytes(ROOM_CELLS)
        self.hearts_left = self._grid.count(Cell.HEART)
        self.room_done = False
        self._emit(EventKind.ROOM_LOADED)

    def _probe(self, i: int, d: int) -> tuple[int, int]:
        """PROBE: (code, index) of the neighbour of i in direction d, or (OUT, -1)."""
        x, y = i % ROOM_W, i // ROOM_W
        nx, ny = x + _DX[d], y + _DY[d]
        if not (0 <= nx < ROOM_W and 0 <= ny < ROOM_H):
            return OUT, -1
        j = i + _DIDX[d]
        return self._grid[j], j

    def _empty(self, i: int, d: int) -> bool:
        return self._probe(i, d)[0] == Cell.EMPTY

    def _scan(self, inp: Input) -> None:
        """SCAN: top-down, left-to-right, in-place, skipping cells moved this tick."""
        g, moved = self._grid, self._moved
        for i in range(ROOM_CELLS):
            if moved[i]:
                continue
            c = g[i]
            if Cell.ANIM0 <= c <= Cell.ANIM6:
                self._emit(EventKind.BLAST_FRAME, i, value=c - Cell.ANIM0)   # SND_REQ frame+4
                g[i] = c + 1 if c < Cell.ANIM6 else Cell.EMPTY
            elif c == Cell.ROCK:
                self._rest_check(i, Cell.ROCK_WAKING)
            elif c == Cell.ROCK_WAKING:
                if self._move_fall(i, Cell.ROCK_FALLING, Cell.ROCK) == LANDED:
                    self._emit(EventKind.ROCK_LANDED, i)
            elif c == Cell.ROCK_FALLING:
                self._fall_step(i, Cell.ROCK_FALLING, Cell.ROCK,
                                (EventKind.ROCK_LANDED, EventKind.ROCK_ROLLED, EventKind.ROCK_HIT))
            elif c == Cell.HEART:
                self._rest_check(i, Cell.HEART_FALLING)     # no waking state for hearts
            elif c == Cell.HEART_FALLING:
                self._fall_step(i, Cell.HEART_FALLING, Cell.HEART,
                                (EventKind.HEART_LANDED, EventKind.HEART_ROLLED, EventKind.HEART_HIT))
            elif c == Cell.BOMB:
                self._rest_check(i, Cell.BOMB_WAKING)
            elif c == Cell.BOMB_WAKING:
                if self._move_fall(i, Cell.BOMB_FALLING, Cell.BOMB) == LANDED:
                    self._emit(EventKind.BOMB_LANDED, i)
            elif c == Cell.BOMB_FALLING:
                self._bomb_fall(i)
            elif c == Cell.BLAST:
                self._blast(i)
            elif c == Cell.HERO:
                self._hero(i, inp)
        moved[:] = bytes(ROOM_CELLS)                        # CLR_MOVED
        self.tick_counter = (self.tick_counter + 1) & 0xFF  # INC TICK (one byte)

    def _rest_check(self, i: int, wake: int) -> None:
        """REST_CHECK: an object at rest decides whether to wake (no movement this tick)."""
        b, _ = self._probe(i, D)
        if b in (Cell.GRASS, Cell.HARD_WALL, Cell.HERO):
            return
        if b == Cell.EMPTY:
            self._grid[i] = wake
            return
        if self._probe(i, U)[0] == wake:                    # quirk: same wake code above
            return
        if (self._empty(i, L) and self._empty(i, DL)) or (self._empty(i, R) and self._empty(i, DR)):
            self._grid[i] = wake

    def _move_fall(self, i: int, falling: int, rest: int) -> int:
        """MOVE_FALL: fall one cell, or roll one diagonal, or land. Returns FELL/ROLLED/LANDED
        (the original returns C=1 for both ROLLED and LANDED, which is what LAND_SOUND uses)."""
        g = self._grid
        g[i] = Cell.EMPTY
        b, j = self._probe(i, D)
        if b == Cell.EMPTY:
            g[j], self._moved[j] = falling, 1
            return FELL
        if b in (Cell.GRASS, Cell.HARD_WALL):
            g[i] = rest
            return LANDED
        if self._empty(i, DL) and self._empty(i, L):
            j = i + _DIDX[DL]
        elif self._empty(i, DR) and self._empty(i, R):
            j = i + _DIDX[DR]
        else:
            g[i] = rest
            return LANDED
        g[j], self._moved[j] = falling, 1
        return ROLLED

    def _fall_step(self, i: int, falling: int, rest: int,
                   kinds: tuple[EventKind, EventKind, EventKind]) -> None:
        """FALL_STEP (rock/heart in flight): hitting hero/bomb detonates the cell below."""
        landed, rolled, hit = kinds
        b, j = self._probe(i, D)
        if b in (Cell.HERO, Cell.BOMB, Cell.BOMB_FALLING):
            self._grid[j] = Cell.BLAST                       # no moved flag: explodes this tick
            self._emit(hit, j)                               # HIT_DETONATE -> LAND_SOUND
            return
        r = self._move_fall(i, falling, rest)
        if r == LANDED:
            self._emit(landed, i)
        elif r == ROLLED:
            self._emit(rolled, i)

    def _bomb_fall(self, i: int) -> None:
        """H_BOMB_FALL."""
        b, j = self._probe(i, D)
        if b == Cell.EMPTY:
            self._move_fall(i, Cell.BOMB_FALLING, Cell.BOMB)
        elif b == Cell.HERO:
            self._grid[j] = Cell.BLAST                       # hero cell explodes this tick
            self._emit(EventKind.BOMB_HIT, j)
        elif b == Cell.GRASS:
            self._grid[i] = Cell.BOMB                        # soft landing
            self._emit(EventKind.BOMB_LANDED, i)
        else:
            self._grid[i] = Cell.BLAST                       # own cell: explodes next tick
            self._emit(EventKind.BOMB_HIT, i)

    def _blast(self, i: int) -> None:
        """H_BLAST: plus-shaped; hard walls and the border survive; resting bombs chain."""
        g, moved = self._grid, self._moved
        written = [i]
        for d in (D, U, R, L):
            b, j = self._probe(i, d)
            if b == OUT or b == Cell.HARD_WALL:
                continue
            g[j] = Cell.BLAST if b in (Cell.BOMB, Cell.BLAST) else Cell.ANIM0
            moved[j] = 1
            written.append(j)
        g[i], moved[i] = Cell.ANIM0, 1
        self._emit(EventKind.BLAST, i, tuple(written))

    def _hero(self, i: int, inp: Input) -> None:
        """H_HERO."""
        if inp is Input.NONE:
            return
        d = inp.value
        if d in (L, R):
            self._push(i, d)
        b, j = self._probe(i, d)
        if b == Cell.EMPTY:
            pass
        elif b == Cell.HEART:
            self.hearts_left -= 1
            self._emit(EventKind.HEART_COLLECTED, j)
        elif b == Cell.GRASS:
            self._emit(EventKind.GRASS_EATEN, j)
        elif b == Cell.EXIT and self.hearts_left == 0:
            self.room_done = True
            self._grid[i] = Cell.EMPTY                       # hero vanishes, exit cell unchanged
            self._emit(EventKind.ROOM_COMPLETE, j)
            return
        else:
            return
        self._grid[j], self._moved[j] = Cell.HERO, 1
        self._grid[i] = Cell.EMPTY

    def _push(self, i: int, d: int) -> None:
        """PUSH: rock/bomb at rest, empty beyond, even tick only."""
        x = i % ROOM_W
        if not 0 <= x + 2 * _DX[d] < ROOM_W:
            return
        b, j = self._probe(i, d)
        if b not in (Cell.ROCK, Cell.BOMB):
            return
        b2, k = self._probe(j, d)
        if b2 != Cell.EMPTY:
            return
        if self.tick_counter & 1:
            return
        self._grid[k], self._moved[k] = b, 1
        self._grid[j] = Cell.EMPTY
        self._emit(EventKind.PUSHED, k)
