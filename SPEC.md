# HEARTLIGHT — Game Engine Specification v2 (derived from disassembly)

Target: pure-logic engine module in Python 3.11+ (stage 3), no rendering, no I/O.
Rendering/input (pygame) is stage 4 and consumes this engine through the API in §8.

Original: Janusz Pelc, 1990, Atari 8-bit, published in Tajemnice ATARI 1/91
(`1_91_heartlight.html`, listing `heartlight.bas`). This version of the spec is
**not a guess**: every rule below was read from the 6502 code in `game.asm`
(labels in `CAPITALS` refer to that file). The previous spec is kept as
`SPEC.v1.md`; where v2 contradicts it, v2 wins.

Residual uncertainties are tagged **[EMU]** — they concern timing/hardware,
not game logic, and can be confirmed in Altirra. Everything else is fixed.

---

## 1. Data model

### 1.1 Grid
- 20 columns × 12 rows, `index = y*20 + x`, y=0 is top. (`GRID` at $9EC0, 240 bytes.)
- Everything outside the grid is **solid** (`PROBE` returns "out", treated as
  occupied, never equal to any cell type). Objects may rest on the grid edge
  (room 3, room 4 bottom pocket). Nothing ever leaves the grid.
- Each cell holds exactly one **code** (§1.2) plus a per-tick `moved` flag
  (bit 7 in the original). The flag is set on every cell an object moves
  *into* during a tick and cleared for all cells at the end of the tick
  (`CLR_MOVED`).

### 1.2 Cell codes
The original keeps object *state* in the cell itself; a falling rock is a
different code than a resting rock. The engine must model all of them.

| code | enum            | level char | notes |
|------|-----------------|------------|-------|
| $20  | EMPTY           | ` `        | |
| $21  | EXIT            | `!`        | solid; opens when `hearts_left == 0`; **destructible by blast** |
| $22  | BOMB_FALLING    | —          | |
| $23  | SOFT_WALL       | `#`        | solid, no handler; destructible; objects roll off it |
| $24  | HEART           | `$`        | at rest |
| $25  | HARD_WALL       | `%`        | indestructible; objects do NOT roll off it |
| $26  | BOMB            | `&`        | at rest; pushable |
| $27  | ROCK            | `@`        | at rest; pushable (loader maps `@` → $27, `PUT_CELL`) |
| $28  | ROCK_FALLING    | —          | |
| $29  | HEART_FALLING   | —          | |
| $2A  | HERO            | `*`        | there may be **several** (room 4 has two) |
| $2B  | BLAST           | —          | explodes when scanned |
| $2D  | BOMB_WAKING     | —          | |
| $2E  | GRASS           | `.`        | solid support; hero consumes it |
| $2F  | ROCK_WAKING     | —          | |
| $30–$36 | ANIM0..ANIM6 | —          | blast animation frames; solid, not walkable |

Object state machines:
- ROCK → ROCK_WAKING → ROCK_FALLING → ROCK
- BOMB → BOMB_WAKING → BOMB_FALLING → BOMB (or BLAST)
- HEART → HEART_FALLING → HEART  (**no waking state** — see §3.5)

"Rounded" does not exist as a concept. Objects roll off *everything* except
GRASS, HARD_WALL and HERO (§3.2).

### 1.3 Level format
Parse `levels.txt`: `[room N]` header followed by exactly 12 lines of 20 chars.
Loader semantics (`PUT_CELL`): characters $20–$2F are stored verbatim; **any
other character becomes ROCK** (that is how `@` becomes $27; a typo letter
would silently become a rock). Room count limit in the original: 30.
Multiple `*` are legal and all of them are live heroes (§4.4).

`hearts_left` = number of HEART cells after loading (`LOAD_ROOM`).

---

## 2. Tick model

The engine is strictly deterministic. `tick(input)` = one scan of the grid.
There are **no phases**. Everything, including the hero, is processed in one
pass in **reading order: y=0..11, x=0..19** (`SCAN`, X = 0..239).

```
for i in 0..239:
    if moved[i]: continue
    c = grid[i]
    if c in ANIM0..ANIM6:  grid[i] = next frame, ANIM6 -> EMPTY; continue
    handler[c](i)          # ROCK, ROCK_WAKING, ROCK_FALLING, HEART, HEART_FALLING,
                           # BOMB, BOMB_WAKING, BOMB_FALLING, BLAST, HERO. Others: no-op.
clear all moved flags
tick_counter += 1
```

Writes are **immediate and in place**. Consequences the implementation must
reproduce exactly:
- An object that moves *down* or *diagonally down* lands at an index not yet
  scanned; the `moved` flag prevents re-processing.
- A cell written **without** the `moved` flag at an index greater than the
  current one **is processed later in the same tick**. This happens in two
  places (`HIT_DETONATE`, `H_BOMB_FALL` hero case): the BLAST written into the
  cell *below* a falling object explodes in the same tick.
- A cell written without `moved` at the current index or a lower one is
  processed next tick (`RC_WAKE`, `BF_EXPLODE`).

Tick rate in the original: one scan every 6 frames (`WAIT_TICK`, CDTMV2=6),
i.e. 8.33 Hz PAL. The engine is tick-pure; the renderer owns the clock.

### 2.1 PROBE (neighbour lookup)
Directions and index deltas (`DX_TAB`/`DY_TAB`/`DIDX_TAB`):

| dir | dx,dy   | delta |
|-----|---------|-------|
| L   | -1, 0   | -1    |
| R   | +1, 0   | +1    |
| U   |  0,-1   | -20   |
| D   |  0,+1   | +20   |
| DL  | -1,+1   | +19   |
| DR  | +1,+1   | +21   |

`probe(i, dir)` returns `OUT` if `x+dx ∉ [0,20)` or `y+dy ∉ [0,12)`, else the
code of that cell (ignoring `moved`). "Empty" means code == EMPTY; `OUT` is
occupied and compares unequal to every code.

---

## 3. Gravity objects (ROCK, HEART, BOMB)

### 3.1 REST_CHECK — object at rest decides whether to wake (`REST_CHECK`)
Called for ROCK (wake code ROCK_WAKING), BOMB (BOMB_WAKING), HEART
(**HEART_FALLING**, directly).

```
b = probe(D)
if b in (GRASS, HARD_WALL, HERO): stay
elif b is EMPTY:                  grid[i] = wake        # no movement this tick
elif probe(U) == wake:            stay                  # quirk, see below
elif probe(L) empty and probe(DL) empty: grid[i] = wake # will roll left
elif probe(R) empty and probe(DR) empty: grid[i] = wake # will roll right
else: stay
```
The wake write does not set `moved` (index already scanned, irrelevant).
Quirk: an object does not start rolling if the cell directly above it holds
the *same wake code* (a just-woken object of the same kind). Implement as-is.

Everything not in (GRASS, HARD_WALL, HERO) — including SOFT_WALL, EXIT,
other objects in any state, BLAST, ANIM frames and `OUT` — is "roll-off-able"
(for `OUT` the diagonal probes are also `OUT`, so nothing happens).

### 3.2 MOVE_FALL — the single movement primitive (`MOVE_FALL`)
`move_fall(i, falling_code, rest_code)`:
```
grid[i] = EMPTY
b = probe(D)
if b is EMPTY:                       grid[i+20] = falling_code, moved
elif b in (GRASS, HARD_WALL):        grid[i]    = rest_code            # land
elif probe(DL) empty and probe(L) empty: grid[i+19] = falling_code, moved   # roll = ONE diagonal move
elif probe(DR) empty and probe(R) empty: grid[i+21] = falling_code, moved
else:                                grid[i]    = rest_code            # land
```
Rolling is a **single diagonal step in one tick**, left first. Note that
`HERO` below is *not* a landing case here: a waking object above a hero rolls
off the hero's head if it can, otherwise lands (returns to rest). It never kills
from this routine.

### 3.3 Waking objects (`H_ROCK_WAKE`, `H_BOMB_WAKE`)
ROCK_WAKING: `move_fall(i, ROCK_FALLING, ROCK)`.
BOMB_WAKING: `move_fall(i, BOMB_FALLING, BOMB)`.
So the first movement happens one tick after waking, and a woken object whose
support reappeared (grass/hard wall below) simply goes back to rest.

### 3.4 Falling rock / falling heart (`H_ROCK_FALL`, `H_HEART_FALL` → `FALL_STEP`)
```
b = probe(D)
if b in (HERO, BOMB, BOMB_FALLING):   grid[i+20] = BLAST   # no moved flag → explodes THIS tick (§5)
                                      # the falling object itself stays in place, unchanged
else: move_fall(i, falling_code, rest_code)
```
Landing (rest) is therefore detected the tick *after* the last move, when the
object finds its support. Landing on BOMB_WAKING does **not** detonate (it
rolls off it or rests on it).

### 3.5 Kill rule
A HERO dies when a cell holding **ROCK_FALLING, HEART_FALLING or
BOMB_FALLING** is scanned with the hero directly below. Because ROCK and BOMB
pass through a waking state without a kill check, **a rock/bomb must have
already moved at least one cell to kill**; a resting rock above the hero never
wakes (§3.1) and a woken one rolls off or rests (§3.2). **HEART has no waking
state**: a heart with empty space below becomes HEART_FALLING at once and, if
the hero steps under it during that tick, kills on the next tick without ever
having moved. (`H_HEART` writes $29 directly.)

### 3.6 Bomb in flight (`H_BOMB_FALL`)
```
b = probe(D)
if b is EMPTY:    move_fall(i, BOMB_FALLING, BOMB)        # incl. rolling
elif b == HERO:   grid[i+20] = BLAST     # no moved → explodes this tick; bomb cell stays BOMB_FALLING
elif b == GRASS:  grid[i] = BOMB         # soft landing, no explosion
else:             grid[i] = BLAST        # own index → explodes NEXT tick
```
"else" includes HARD_WALL, SOFT_WALL, ROCK/HEART in any state, another bomb,
EXIT, ANIM frames and the grid border. A bomb that rolls off something lands
next tick on whatever is below and explodes unless that is grass.

---

## 4. Hero (`H_HERO`)

Input per tick: one of {NONE, LEFT, RIGHT, UP, DOWN}. The original picks a
single direction from a 16-entry table (`KEYTAB`); diagonal joystick positions
match nothing and mean NONE. Each HERO cell runs this handler when the scan
reaches it, with the same input.

```
if input is NONE: return
if input in (LEFT, RIGHT): push(i, dir)          # §4.1, may free the target
b = probe(dir)
if b is EMPTY:                          move
elif b == HEART:   hearts_left -= 1;    move
elif b == GRASS:                        move
elif b == EXIT and hearts_left == 0:    room_done = True; grid[i] = EMPTY   # hero vanishes (§4.3)
else: no-op
```
`move`: `grid[target] = HERO, moved; grid[i] = EMPTY`.
Not enterable: any wall, resting/waking/falling rock or bomb, HEART_FALLING
(a falling heart cannot be collected), BLAST, ANIM frames, closed EXIT,
another HERO.

### 4.1 Push (`PUSH`)
Horizontal only. Conditions, all required:
1. `x + 2*dx` inside the grid;
2. the neighbour is **ROCK** or **BOMB at rest** (waking/falling ones cannot be pushed);
3. the cell beyond the neighbour is EMPTY;
4. `tick_counter` is **even** (`LDA TICK; LSR; BCS fail`) — pushing succeeds at
   most every other tick; holding the direction retries automatically.
Effect: `grid[beyond] = neighbour code (rest), moved; grid[neighbour] = EMPTY`.
The hero then moves into the vacated cell in the same handler call. Pushing a
bomb never detonates it. Pushed objects keep their rest code and wake next
tick if unsupported.

### 4.2 Tick counter
`tick_counter` starts at 0 at engine construction and increments after every
scan. [EMU: the original uses an uninitialised zero-page byte, so the parity
phase at game start is arbitrary; 0 is the chosen convention.]

### 4.3 Exit
When hearts_left == 0 the exit is open (the original only blinks the tile,
`H_EXIT`). Entering it removes the hero from the grid and sets `room_done`.
Any hero reaching the exit completes the room, even if other heroes remain.
The exit is a normal solid cell for gravity objects (they roll off it) and is
**destroyed by a blast** — the room then becomes unwinnable. Reproduce this.

### 4.4 Several heroes
All HERO cells are controlled simultaneously by the same input, each processed
at its own position in scan order. Death = **no HERO cell left** after the
tick (`COUNT_CELLS('*') == 0`). Room 4 relies on this.

---

## 5. Explosions (`H_BLAST`)

A BLAST cell, when scanned, does:
```
for dir in (D, U, R, L):
    b = probe(dir)
    if b is OUT or b == HARD_WALL: continue
    if b in (BOMB, BLAST): grid[j] = BLAST, moved      # chain: explodes NEXT tick
    else:                  grid[j] = ANIM0, moved      # destroyed
grid[i] = ANIM0, moved
```
- Blast shape is a **plus (5 cells)**, not 3×3.
- Destroys: SOFT_WALL, GRASS, ROCK/HEART/BOMB in *falling or waking* state,
  HERO, EXIT, ANIM frames, EMPTY (harmless). Survives: HARD_WALL, border.
- Only a **BOMB at rest** chains; BOMB_WAKING/BOMB_FALLING caught in a blast
  are simply destroyed.
- **Destroyed hearts do not change `hearts_left`** (the only decrement is on
  collection, `ENTER_CELL`). The room becomes unwinnable. Reproduce this.
- ANIM frames: the cell is ANIM0 in the tick it is created and advances one
  frame per subsequent tick; after ANIM6 it becomes EMPTY. It is therefore
  non-empty and solid for **7 ticks** (creation tick + 6). ANIM cells do not
  kill and cannot be entered or pushed; objects roll off them.

How BLAST cells come into existence:
- falling rock/heart with HERO, BOMB or BOMB_FALLING below → BLAST in the cell
  below, **same tick** (§3.4);
- falling bomb with HERO below → BLAST in hero cell, same tick; falling bomb
  hitting anything but grass/empty → BLAST in its own cell, next tick (§3.6);
- chain from another blast → next tick;
- ESC key → every HERO becomes BLAST (suicide), exploded during the death
  sequence (§6).

---

## 6. Win / death / lives / rooms (`MAIN_LOOP`)

After each tick, in this order:
1. if `room_done`: advance room (§6.1);
2. else if no HERO cell exists: death sequence (§6.2).

### 6.1 Room advance (`ROOM_DONE`)
```
room += 1
if room >= n_rooms: room = 0          # the game loops forever; there is no ending
extra_counter -= 1
if extra_counter == 0:
    lives = min(lives + 1, 255)
    extra_counter = extra            # meta.json "extra" = rooms per bonus life (article confirms)
load room
```

### 6.2 Death sequence (`HERO_DEAD`, `DEATH_WAIT`)
The engine keeps ticking with input NONE for `DEATH_TICKS` ticks so the
explosion plays out [EMU: original waits 64 frames ≈ 10–11 scans;
`DEATH_TICKS = 10`], then:
```
lives -= 1
if lives < 0: game over (title screen)
else: reload the same room pristine
```
Note: `lives` is displayed and counts down **to 0 and continues**; with the
default `lives = 3` the player gets **four** attempts. Reproduce this.

### 6.3 Initial state (`TITLE_INIT`, `LOAD_ROOM`)
`lives = meta.lives (3)`, `extra_counter = meta.extra (2)`, `room = 0`,
`tick_counter = 0`, all cells at rest as loaded, `hearts_left = count('$')`.
The loading "curtain" animation is a renderer concern.

---

## 7. Things the engine does NOT do
No sub-tick hero movement, no probability, no "grab without moving", no
magic walls, no amoeba, no score, no time limit, no level ending.

### 7.1 Sound (renderer, for reference)
`SND_REQ` keeps the highest priority requested during a scan; `SND_PLAY` then
programs POKEY channel 1 for exactly one frame. Request sites: grass eaten
and push = 1; rock landed/rolled/hit, bomb landed/hit = 2; heart collected/
landed/rolled/hit and every curtain frame = 3; a blast animation cell that
advances from frame f = f+4. Registers by priority p (Y = p-1):
Y=0 AUDF $00 AUDC $81; Y=1 AUDF $04 AUDC $04; Y=2 AUDF (RANDOM&15)+8 AUDC
$A4; Y>=3 AUDF $10 AUDC Y. The engine emits one Event per request site so a
renderer can reproduce this (`heartlight/render.py`, `Sounds`).

---

## 8. Engine API (stage 3 deliverable)

```python
class Input(Enum): NONE; LEFT; RIGHT; UP; DOWN

class Cell(IntEnum):          # values = original codes, useful for tests/dumps
    EMPTY=0x20; EXIT=0x21; BOMB_FALLING=0x22; SOFT_WALL=0x23; HEART=0x24
    HARD_WALL=0x25; BOMB=0x26; ROCK=0x27; ROCK_FALLING=0x28; HEART_FALLING=0x29
    HERO=0x2A; BLAST=0x2B; BOMB_WAKING=0x2D; GRASS=0x2E; ROCK_WAKING=0x2F
    ANIM0=0x30; ...; ANIM6=0x36

@dataclass(frozen=True)
class Event:                  # renderer/audio hooks, emitted in scan order
    kind: EventKind           # HEART_COLLECTED, GRASS_EATEN, PUSHED,
                              # ROCK_LANDED/ROLLED/HIT, HEART_LANDED/ROLLED/HIT,
                              # BOMB_LANDED/HIT, BLAST(cells), BLAST_FRAME(value),
                              # HERO_DIED, ROOM_COMPLETE, ROOM_LOADED, EXTRA_LIFE, GAME_OVER
    cell: int | None          # index, when meaningful
    cells: tuple[int, ...]    # BLAST: cells written
    value: int                # BLAST_FRAME: frame before advancing (0..6)

class Engine:
    def __init__(self, rooms: list[str], *, lives: int = 3, extra: int = 2): ...
    def tick(self, inp: Input) -> list[Event]: ...   # one scan + post-tick bookkeeping
    @property
    def grid(self) -> Sequence[Cell]: ...             # 240 cells, read-only view
    @property
    def state(self) -> GameState: ...                 # hearts_left, lives, room, tick, status

def parse_levels(text: str) -> list[str]: ...         # levels.txt -> 12*20-char room strings
```

Hard requirements:
- Zero dependencies beyond stdlib. Fully deterministic: same rooms + same input
  sequence ⇒ identical state (property-test this).
- The scan must be implemented literally as in §2 (single pass, in-place
  writes, `moved` flags), not as "collect then apply". Several tests below
  depend on same-tick propagation.
- `[EMU]` values (`DEATH_TICKS`, initial tick parity) as module-level constants.
- Type-annotated, mypy-clean.

---

## 9. Acceptance tests (pytest)

Mini-grids use the level ASCII, 20×12 with explicit `%` frame unless stated.
"t=N" means the state observed after N calls to `tick`. Column notation is
top→bottom.

**T1 straight fall.** `@` with 3 EMPTY below, floor under.
t=1: ROCK_WAKING in place. t=2,3,4: ROCK_FALLING one cell lower each tick.
t=5: ROCK at rest on the floor. Never more than one cell per tick.

**T2 stack, no tunnelling (scan order).** Column `@ / @ / EMPTY / %`, walls at
both sides. t=1: lower rock ROCK_WAKING, upper unchanged. t=2: lower moves
down (ROCK_FALLING), upper still ROCK. t=3: lower rests (ROCK); upper wakes.
t=4: upper moves. t=5: upper rests on lower. Stacked objects fall with gaps —
this is what distinguishes top-down scan from bottom-up.

**T3 roll.** `@` on `@` on floor, cells L, DL, R, DR of the upper rock EMPTY.
t=1: upper becomes ROCK_WAKING in place. t=2: upper moves **diagonally** to
(x-1, y+1) as ROCK_FALLING. t=3: it rests (ROCK) on the floor, beside the
lower rock. With L blocked and R free, it goes to (x+1, y+1) instead.

**T4 kill.** Column `@ / EMPTY / *`. t=1: ROCK_WAKING. t=2: ROCK_FALLING
directly above hero. t=3: hero cell becomes BLAST and explodes **in the same
tick**: hero, the rock above and the L/R/D neighbours (unless `%`) become
ANIM0; `tick` returns HERO_DIED; the engine enters the death sequence.

**T4b no kill without movement.** `@` directly above `*` from level start:
nothing ever happens. Variant: `@` with EMPTY below, hero beside that empty
cell, input toward it. t=1: rock wakes AND hero steps under it. t=2: rock
(ROCK_WAKING) rolls off the hero if a diagonal is free, otherwise returns to
ROCK. The hero survives. Same setup with `$` instead of `@`: t=1 heart becomes
HEART_FALLING, hero steps under; t=2 hero dies.

**T5 push.** Row `* @ EMPTY`, input RIGHT, tick_counter even → rock and hero
shift one cell; ROCK keeps rest state and wakes next tick if unsupported.
Same on an odd tick → nothing; the following tick succeeds. `* @ %` → no-op.
`* & EMPTY` → bomb is pushed and does not explode. `* ( EMPTY` (falling rock)
→ no-op. Vertical push → no-op.

**T6 bomb hit and chain.** `@` above EMPTY above `&`; a second `&` directly
left of the first; a `%` directly right of the first. t=1: wake. t=2: rock
falls to just above the bomb. t=3: rock scans, bomb cell becomes BLAST and
explodes this tick: rock → ANIM0, bomb cell → ANIM0, `%` untouched, left bomb
→ BLAST (moved). t=4: left bomb explodes (its own plus). A bomb placed
diagonally is never affected. ANIM cells become EMPTY 7 ticks after creation.

**T7 grass support.** `@` on `.`, hero left of the grass, input RIGHT.
t=1: hero eats the grass and stands under the rock; rock stays (hero below).
Input LEFT: t=2: hero leaves; rock still ROCK (it was scanned before the hero
moved). t=3: ROCK_WAKING. t=4: rock falls into the former grass cell.

**T8 win gating and exit removal.** Entering `!` with hearts_left > 0 → no-op.
Collecting the last heart then entering → `room_done`, hero cell EMPTY, the
`!` cell unchanged, ROOM_COMPLETE event; next tick loads the next room.

**T9 unwinnable by blast.** A heart inside a blast plus → ANIM0, hearts_left
unchanged; an `!` inside the plus → ANIM0 then EMPTY.

**T10 falling bomb.** `&` above 2 EMPTY above `.` → t=1 wake, t=2,3 fall,
t=4 lands: BOMB at rest, no explosion. Same over `%` or `@` → t=4 own cell
becomes BLAST, t=5 explodes. `&` above EMPTY above `*` → t=3 hero cell BLAST
and explodes in the same tick.

**T11 two heroes.** Two `*`, input RIGHT: both move. Kill one: game continues.
Kill both: death sequence. One enters the open exit: room complete.

**T12 lives.** lives=3: after 3 deaths lives==0 and the room reloads; the 4th
death is GAME_OVER.

**T13 determinism.** Random rooms + random input sequences: two engines fed
the same data produce identical grids after every tick (hypothesis).

---

## 10. Non-goals (stage 3)
No rendering, no sound, no timing/FPS, no curtain animation, no key mapping,
no save states. Stage 4: pygame rendering, 2×2 tiles per cell as in `RENDER`
(tile table `TILE_TAB`, charset at bin offset 0, PAL registers 708–712 =
`[4,6,14,10,0]` from `meta.json`), reading Events for sound/effects.
