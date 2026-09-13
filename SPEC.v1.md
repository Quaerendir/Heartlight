# HEARTLIGHT — Game Engine Specification (clean-room reimplementation)

Target: pure-logic engine module in Python 3.11+ (stage 3), no rendering, no I/O.
Rendering/input (pygame) is stage 4 and consumes this engine through the API below.

Original: Janusz Pelc, 1990, Atari 8-bit (Tajemnice ATARI). This spec is a
clean-room reconstruction: level data is extracted from the original
(`levels.txt`), rules are specified from the Boulder-Dash-family canon and the
Heartlight lineage. Every rule carries a confidence tag:

- **[DATA]** — proven by extracted level data.
- **[BD]** — standard Boulder-Dash-family behavior, safe to implement as-is.
- **[VERIFY]** — plausible but must be validated against the original running
  in an emulator (Altirra) before being frozen. Implement behind a clearly
  named constant/flag so it can be flipped without refactoring.

---

## 1. Data model

### 1.1 Grid
- Fixed 20 columns x 12 rows. `grid[y][x]`, y=0 is top. [DATA]
- Everything outside the grid behaves as HARD_WALL (virtual border). Objects
  may occupy edge cells; nothing ever leaves the grid. [DATA — room 3 has
  objects resting on grid edges with no wall row beneath]

### 1.2 Cell types (from level ASCII)

| char | enum        | walkable | gravity | rounded | destructible |
|------|-------------|----------|---------|---------|--------------|
| `%`  | HARD_WALL   | no       | no      | no      | no           |
| `#`  | SOFT_WALL   | no       | no      | no      | yes (blast)  |
| `@`  | ROCK        | pushable | yes     | yes     | yes (blast)  |
| `$`  | HEART       | collect  | yes     | yes     | yes (blast)  |
| `*`  | HERO        | —        | no      | no      | yes (blast)  |
| `!`  | EXIT        | when open| no      | no      | no [VERIFY]  |
| `&`  | BOMB        | pushable [VERIFY] | yes | yes | triggers      |
| `.`  | GRASS       | yes (consumed) | no | no   | yes (blast)  |
| ` `  | EMPTY       | yes      | —       | no      | —            |

- "rounded" = other rounded objects roll off it (§3.2).
- Grass is solid support: objects rest on grass and do NOT fall through it. [BD]

### 1.3 Level format
Parse `levels.txt`: `[room N]` header followed by exactly 12 lines of 20 chars.
Exactly one HERO per room is expected; **if more than one `*` occurs, take the
first in scan order (top-left → bottom-right) and treat the rest as GRASS
[VERIFY — room 4 in the extracted data contains two `*`; confirm original
behavior on emulator]**.

---

## 2. Tick model

The engine is strictly deterministic. One call to `tick(input)` advances the
world by exactly one physics step. Order within a tick:

1. **Hero phase** — apply player input (§4).
2. **Physics phase** — one full gravity/roll scan (§3).
3. **Resolution phase** — apply queued explosions (§5), evaluate win/death (§6).

Hero moves at tick granularity; do NOT implement sub-tick hero movement in the
engine (smooth animation is a renderer concern, interpolate there). [VERIFY —
in the original the hero may move faster than the physics rate; if emulator
testing shows e.g. 2 hero steps per physics step, expose it as
`HERO_STEPS_PER_TICK` and keep the engine tick-pure]

### 2.1 Physics scan — the critical part
Scan the grid **bottom-up, left-to-right** (y from H-1 down to 0). For each
cell containing an object with gravity, resolve fall/roll immediately
(write-in-place into the same grid).

Maintain a per-object `falling: bool` flag (needed for kill-on-head and bomb
triggers). A per-tick `moved` flag set is NOT required with bottom-up scan for
straight falls (a moved object lands below the scan line, so it cannot be
re-processed this tick), **but rolls move objects sideways/down into cells not
yet scanned on the row above — set `moved` on rolled objects and skip
already-moved objects for the remainder of the scan** to prevent double-moves.
This is the classic BD chain-reaction pitfall; get it wrong and a rock
teleports 2+ cells in one tick. [BD]

---

## 3. Gravity objects (ROCK, HEART, BOMB)

### 3.1 Falling
- If the cell directly below is EMPTY → move down one cell, set `falling`. [BD]
- If the object is `falling` and the cell below is now occupied → it **lands**:
  clear `falling`, then check landing triggers (§3.3, §5). [BD]

### 3.2 Rolling
If the cell below is occupied by a **rounded** object (ROCK, HEART, BOMB) or
[VERIFY] HARD/SOFT wall, then:
- if `left` AND `below-left` are both EMPTY → move one cell left, set `falling`;
- else if `right` AND `below-right` are both EMPTY → move one cell right, set
  `falling`. Left-first priority. [BD; VERIFY the left-first tie-break and
  whether objects roll off flat walls — in classic BD they roll off walls too,
  in some Heartlight ports only off rounded objects]
- Objects never roll off GRASS or the HERO. [BD]

### 3.3 Landing on the hero / on a bomb
- A `falling` object entering the cell above the hero does NOT kill; a
  `falling` object moving INTO the hero's cell cannot happen (hero occupies
  it) — the kill rule is: **object lands on top of hero = the cell below the
  falling object is HERO → hero dies** (§6). A resting object adjacent to the
  hero never kills. [BD]
- A `falling` object landing on a BOMB detonates that bomb (queued for §5). [BD]
- A `falling` BOMB that lands on anything detonates itself. [VERIFY — in
  Heartlight PC bombs explode on impact after any fall; confirm for the 8-bit
  original. Implement as `BOMB_EXPLODES_ON_LANDING = True`]

---

## 4. Hero

Input per tick: one of {NONE, UP, DOWN, LEFT, RIGHT}. Diagonals do not exist.

Target cell resolution:
- EMPTY, GRASS → move in; grass becomes EMPTY. [BD]
- HEART → collect: `hearts_left -= 1`, move in. [BD/DATA]
- EXIT and exit is open (`hearts_left == 0`) → level complete. Exit while
  closed = solid wall. [BD] [VERIFY — whether the exit is visibly closed/open]
- ROCK, horizontal input only: if the cell beyond the rock (same direction) is
  EMPTY → rock shifts one cell, hero moves in. Pushing is instant (no BD-style
  probability/delay) [VERIFY]. Rocks cannot be pushed up/down. A `falling`
  rock cannot be pushed. [BD]
- BOMB pushable like a rock [VERIFY — flag `BOMB_PUSHABLE`; pushing a bomb
  must NOT detonate it if enabled].
- HARD_WALL, SOFT_WALL, closed EXIT, anything else → no-op.

There is no "grab without moving" (BD's ctrl-move). [VERIFY]

---

## 5. Explosions

Trigger: falling object lands on a BOMB, or a falling BOMB lands (§3.3), or a
BOMB is caught in another blast (chain reaction).

- Blast area: 3x3 centered on the bomb. [BD/Heartlight canon]
- Destroys: SOFT_WALL, GRASS, ROCK, HEART, BOMB (chains), HERO (death).
  Does NOT destroy: HARD_WALL, EXIT [VERIFY for EXIT]. Grid border is
  indestructible.
- Destroyed HEARTs do NOT decrement `hearts_left` — wait: they MUST decrement
  the *remaining requirement*? **No.** Rule: `hearts_left` counts hearts still
  on the grid that must be collected; a heart destroyed by a blast is removed
  from the grid, therefore `hearts_left -= 1` (the level remains solvable).
  [VERIFY — alternative: destroyed hearts make the level unwinnable; Heartlight
  PC decrements. Implement decrement, flag `BLAST_CONSUMES_HEART_REQUIREMENT`]
- Chained bombs detonate on the **next** tick (queue), not recursively within
  the same tick — this keeps propagation observable and deterministic. [BD]
- Blast cells become EMPTY at the end of the resolution phase. [VERIFY —
  some BD-likes leave transient "explosion" cells for 1-2 ticks; renderer can
  fake this, keep the engine instant]

---

## 6. Win / death / lives

- Win room: hero enters open EXIT.
- Death: falling object lands on hero, or hero inside a blast. On death:
  `lives -= 1`; if `lives > 0` → reload current room pristine; else game over.
- Initial `lives = 3`; `extra = 2` [DATA, meaning uncertain — likely bonus-life
  parameter; VERIFY. Not needed for a playable stage-3 engine].
- Room order: 1→4, game complete after room 4 (this extract has 4 rooms; the
  full game had more). [DATA]

---

## 7. Engine API (stage 3 deliverable)

```python
class Input(Enum): NONE; UP; DOWN; LEFT; RIGHT

@dataclass
class Event: ...   # HEART_COLLECTED, ROCK_LANDED, EXPLOSION(cells), HERO_DIED,
                   # ROOM_COMPLETE, GAME_OVER — for renderer/audio hooks

class Engine:
    def __init__(self, level: str, *, lives: int = 3): ...
    def tick(self, inp: Input) -> list[Event]: ...
    @property
    def grid(self) -> list[list[Cell]]: ...   # read-only view
    @property
    def state(self) -> GameState: ...         # hearts_left, lives, status
```

Hard requirements:
- Zero dependencies beyond stdlib. Fully deterministic: same level + same input
  sequence ⇒ identical state (property-test this).
- All [VERIFY] behaviors behind module-level constants, defaults as specified.
- Type-annotated, mypy-clean.

## 8. Acceptance tests (implement as pytest fixtures)

Mini-grids use the same ASCII; border rows omitted for brevity but tests must
pad with virtual border semantics or include explicit `%` frames.

T1 straight fall: `@` with 3 EMPTY below → exactly 1 cell per tick, 3 ticks to
rest, `falling` true during, false after.

T2 no tunneling (chain fall): column `@ / @ / (empty) / %` — after 1 tick the
lower rock rests, upper rock moved 1; never 2 cells in one tick.

T3 roll: `@` on top of `@` on floor, both sides free → upper rock rolls LEFT
(left-first), lands after 2 ticks total.

T4 kill: hero under an `@` with one EMPTY between → tick1: rock falls, now
directly above hero, `falling`; tick2: rock cannot enter hero cell but rule
§3.3 fires → HERO_DIED. A rock resting directly above the hero from level
start never kills.

T5 push: `* @ (empty)` + RIGHT → hero and rock shift; `* @ %` + RIGHT → no-op.

T6 bomb chain: `@` falls onto `&`, second `&` inside the 3x3 → tick N:
EXPLOSION #1; tick N+1: EXPLOSION #2. HARD_WALL in blast survives.

T7 grass support: `@` resting on `.` stays; hero eats the grass from the side;
next tick the rock falls.

T8 win gating: collecting last heart opens exit; entering exit before that is
a no-op.

## 9. Non-goals (stage 3)
No rendering, no sound, no timing/FPS, no scoring, no charset extraction, no
save states. Stage 4 adds pygame rendering (colors from meta.json: PAL
registers 708-712 = [4,6,14,10,0]) reading Events for effects.
