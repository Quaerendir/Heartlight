"""Acceptance tests from SPEC.md §9. Tick counts are traced from game.asm."""
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from heartlight import (Cell, Engine, EventKind, Input, Status, DEATH_TICKS, ROOM_W,
                        parse_levels)

C = Cell
NONE, LEFT, RIGHT, UP, DOWN = Input.NONE, Input.LEFT, Input.RIGHT, Input.UP, Input.DOWN


def idx(x: int, y: int) -> int:
    return y * ROOM_W + x


def room(*rows: str, hero: bool = True) -> str:
    """Small ASCII picture placed top-left in a 20x12 grid of hard walls.
    A spare hero is walled in at (18,10) so physics-only tests do not trigger death."""
    grid = ['%' * 20 for _ in range(12)]
    for y, r in enumerate(rows):
        grid[y] = (r + '%' * 20)[:20]
    if hero:
        grid[10] = '%' * 18 + '*%'
    return ''.join(grid)


def run(e: Engine, n: int, inp: Input = NONE) -> list:
    ev: list = []
    for _ in range(n):
        ev = e.tick(inp)
    return ev


def kinds(events) -> list[EventKind]:
    return [ev.kind for ev in events]


def cells_of(e: Engine, code: Cell) -> list[int]:
    return [i for i, c in enumerate(e.grid) if c == code]


# ---------------------------------------------------------------- T1
def test_t1_straight_fall_one_cell_per_tick_wake_first():
    e = Engine([room('%@%', '% %', '% %', '% %')])
    assert e.grid[idx(1, 0)] == C.ROCK
    run(e, 1)
    assert e.grid[idx(1, 0)] == C.ROCK_WAKING
    for t, y in ((2, 1), (3, 2), (4, 3)):
        run(e, 1)
        assert e.grid[idx(1, y)] == C.ROCK_FALLING, t
        assert e.grid[idx(1, y - 1)] == C.EMPTY
    ev = run(e, 1)
    assert e.grid[idx(1, 3)] == C.ROCK
    assert EventKind.ROCK_LANDED in kinds(ev)


# ---------------------------------------------------------------- T2
def test_t2_stack_falls_with_gaps_top_down_scan():
    e = Engine([room('%@%', '%@%', '% %')])
    top, mid, low = idx(1, 0), idx(1, 1), idx(1, 2)
    run(e, 1)
    assert (e.grid[top], e.grid[mid]) == (C.ROCK, C.ROCK_WAKING)
    run(e, 1)
    assert (e.grid[top], e.grid[mid], e.grid[low]) == (C.ROCK, C.EMPTY, C.ROCK_FALLING)
    run(e, 1)
    assert (e.grid[top], e.grid[low]) == (C.ROCK_WAKING, C.ROCK)
    run(e, 1)
    assert (e.grid[top], e.grid[mid]) == (C.EMPTY, C.ROCK_FALLING)
    run(e, 1)
    assert (e.grid[mid], e.grid[low]) == (C.ROCK, C.ROCK)


# ---------------------------------------------------------------- T3
def test_t3_roll_is_one_diagonal_step_left_first():
    e = Engine([room('% @ %', '% @ %')])
    run(e, 1)
    assert e.grid[idx(2, 0)] == C.ROCK_WAKING
    run(e, 1)
    assert e.grid[idx(2, 0)] == C.EMPTY
    assert e.grid[idx(1, 1)] == C.ROCK_FALLING
    ev = run(e, 1)
    assert e.grid[idx(1, 1)] == C.ROCK
    assert EventKind.ROCK_LANDED in kinds(ev)


def test_t3_roll_right_when_left_blocked():
    e = Engine([room('%%@ %', '%%@ %')])
    run(e, 2)
    assert e.grid[idx(3, 1)] == C.ROCK_FALLING
    run(e, 1)
    assert e.grid[idx(3, 1)] == C.ROCK


# ---------------------------------------------------------------- T4
def test_t4_falling_rock_kills_and_explodes_same_tick():
    e = Engine([room('%@%', '% %', '%*%', hero=False)])
    run(e, 2)
    assert e.grid[idx(1, 1)] == C.ROCK_FALLING
    assert e.grid[idx(1, 2)] == C.HERO
    ev = run(e, 1)
    assert EventKind.BLAST in kinds(ev) and EventKind.HERO_DIED in kinds(ev)
    assert e.grid[idx(1, 2)] == C.ANIM0
    assert e.grid[idx(1, 1)] == C.ANIM0           # the rock above is destroyed too
    assert e.grid[idx(0, 2)] == C.HARD_WALL and e.grid[idx(2, 2)] == C.HARD_WALL
    assert e.state.status is Status.DYING


def test_t4b_resting_rock_above_hero_never_kills():
    e = Engine([room('%@%', '%*%', hero=False)])
    before = e.grid
    run(e, 20)
    assert e.grid == before
    assert e.state.status is Status.PLAYING


def test_t4b_waking_rock_rolls_off_hero_head():
    e = Engine([room('%@ %', '% *%', hero=False)])
    e.tick(LEFT)
    assert e.grid[idx(1, 0)] == C.ROCK_WAKING and e.grid[idx(1, 1)] == C.HERO
    e.tick(NONE)
    assert e.grid[idx(1, 1)] == C.HERO
    assert e.grid[idx(2, 1)] == C.ROCK_FALLING     # rolled down-right
    run(e, 5)
    assert e.state.status is Status.PLAYING


def test_t4b_waking_rock_returns_to_rest_on_hero():
    e = Engine([room('%@%', '% *%', hero=False)])
    e.tick(LEFT)
    e.tick(NONE)
    assert e.grid[idx(1, 0)] == C.ROCK and e.grid[idx(1, 1)] == C.HERO
    run(e, 5)
    assert e.state.status is Status.PLAYING


def test_t4b_heart_has_no_waking_state_and_kills():
    e = Engine([room('%$ %', '% *%', hero=False)])
    e.tick(LEFT)
    assert e.grid[idx(1, 0)] == C.HEART_FALLING and e.grid[idx(1, 1)] == C.HERO
    ev = e.tick(NONE)
    assert EventKind.HERO_DIED in kinds(ev)


# ---------------------------------------------------------------- T5
def test_t5_push_rock_on_even_tick():
    e = Engine([room('%*@ %', hero=False)], initial_tick=0)
    assert e.state.tick == 0
    ev = e.tick(RIGHT)
    assert EventKind.PUSHED in kinds(ev)
    assert e.grid[idx(2, 0)] == C.HERO and e.grid[idx(3, 0)] == C.ROCK


def test_t5_push_fails_on_odd_tick_then_succeeds():
    e = Engine([room('%*@ %', hero=False)], initial_tick=0)
    e.tick(NONE)                                   # tick counter -> 1
    e.tick(RIGHT)
    assert e.grid[idx(1, 0)] == C.HERO and e.grid[idx(2, 0)] == C.ROCK
    ev = e.tick(RIGHT)
    assert EventKind.PUSHED in kinds(ev)
    assert e.grid[idx(2, 0)] == C.HERO and e.grid[idx(3, 0)] == C.ROCK


def test_t5_push_blocked_by_wall():
    e = Engine([room('%*@%', hero=False)], initial_tick=0)
    e.tick(RIGHT)
    assert e.grid[idx(1, 0)] == C.HERO and e.grid[idx(2, 0)] == C.ROCK


def test_t5_push_bomb_does_not_detonate():
    e = Engine([room('%*& %', hero=False)], initial_tick=0)
    e.tick(RIGHT)
    assert e.grid[idx(3, 0)] == C.BOMB and e.grid[idx(2, 0)] == C.HERO
    run(e, 5)
    assert C.BLAST not in e.grid and C.ANIM0 not in e.grid


def test_t5_cannot_push_falling_rock_or_vertically():
    e = Engine([room('%*( %', hero=False)], initial_tick=0)       # '(' loads verbatim as ROCK_FALLING
    e.tick(RIGHT)
    assert e.grid[idx(1, 0)] == C.HERO
    e = Engine([room('%@%', '%*%', hero=False)])
    e.tick(UP)
    assert e.grid[idx(1, 0)] == C.ROCK and e.grid[idx(1, 1)] == C.HERO


def test_t5_pushed_rock_keeps_rest_state_then_wakes():
    e = Engine([room('%*@ %', '%%% %', hero=False)], initial_tick=0)
    e.tick(RIGHT)
    assert e.grid[idx(3, 0)] == C.ROCK
    e.tick(NONE)
    assert e.grid[idx(3, 0)] == C.ROCK_WAKING
    e.tick(NONE)
    assert e.grid[idx(3, 1)] == C.ROCK_FALLING


# ---------------------------------------------------------------- T6
def test_t6_rock_on_bomb_explodes_same_tick_plus_shape_and_chain():
    #  y0: % . @ . %      rock at (2,0)
    #  y1: % . . & %      bystander bomb at (3,1), diagonal to the blast
    #  y2: % & & % %      bombs at (1,2) and (2,2), hard wall at (3,2)
    e = Engine([room('% @ %', '%  &%', '%&&%%')])
    run(e, 2)
    assert e.grid[idx(2, 1)] == C.ROCK_FALLING
    ev = run(e, 1)
    blasts = [x for x in ev if x.kind == EventKind.BLAST]
    assert len(blasts) == 1 and blasts[0].cell == idx(2, 2)
    assert set(blasts[0].cells) == {idx(2, 2), idx(2, 1), idx(1, 2)}
    assert e.grid[idx(2, 2)] == C.ANIM0
    assert e.grid[idx(2, 1)] == C.ANIM0            # the falling rock is gone
    assert e.grid[idx(1, 2)] == C.BLAST            # chained, explodes next tick
    assert e.grid[idx(3, 2)] == C.HARD_WALL
    assert e.grid[idx(3, 1)] == C.BOMB             # diagonal: untouched
    ev = run(e, 1)
    assert [x.cell for x in ev if x.kind == EventKind.BLAST] == [idx(1, 2)]
    assert e.grid[idx(1, 2)] == C.ANIM0
    assert e.grid[idx(1, 1)] == C.ANIM0
    assert e.grid[idx(2, 1)] == C.ANIM1
    assert e.grid[idx(3, 1)] == C.BOMB
    # (1,1) created at t=4: solid for 7 ticks, empty at t=11
    run(e, 6)
    assert e.grid[idx(1, 1)] == C.ANIM6
    run(e, 1)
    assert e.grid[idx(1, 1)] == C.EMPTY
    assert e.grid[idx(3, 1)] == C.BOMB


# ---------------------------------------------------------------- T7
def test_t7_grass_supports_rock_until_hero_leaves():
    e = Engine([room('% @ %', '%*.%%', hero=False)])
    rock, grass = idx(2, 0), idx(2, 1)
    ev = e.tick(RIGHT)
    assert EventKind.GRASS_EATEN in kinds(ev)
    assert e.grid[grass] == C.HERO and e.grid[rock] == C.ROCK
    e.tick(LEFT)
    assert e.grid[idx(1, 1)] == C.HERO and e.grid[rock] == C.ROCK
    e.tick(NONE)
    assert e.grid[rock] == C.ROCK_WAKING
    e.tick(NONE)
    assert e.grid[grass] == C.ROCK_FALLING
    e.tick(NONE)
    assert e.grid[grass] == C.ROCK


# ---------------------------------------------------------------- T8
def test_t8_exit_closed_until_last_heart():
    e = Engine([room('%*!%', '%$%%', hero=False)])
    e.tick(RIGHT)
    assert e.grid[idx(1, 0)] == C.HERO and not e.state.room_done


def test_t8_win_removes_hero_and_loads_next_room():
    r1 = room('%*$!%', hero=False)
    r2 = room('%*%', hero=False)
    e = Engine([r1, r2])
    ev = e.tick(RIGHT)
    assert EventKind.HEART_COLLECTED in kinds(ev) and e.state.hearts_left == 0
    ev = e.tick(RIGHT)
    assert EventKind.ROOM_COMPLETE in kinds(ev)
    assert e.grid[idx(2, 0)] == C.EMPTY and e.grid[idx(3, 0)] == C.EXIT
    assert e.state.room_done and e.state.room == 1
    ev = e.tick(NONE)
    assert EventKind.ROOM_LOADED in kinds(ev)
    assert e.grid[idx(1, 0)] == C.HERO and e.grid[idx(3, 0)] == C.HARD_WALL


def test_t8_rooms_wrap_and_extra_life_every_extra_rooms():
    r = room('%*!%', hero=False)
    e = Engine([r], lives=3, extra=2)
    e.tick(RIGHT)
    assert e.state.room == 0 and e.state.lives == 3 and e.state.extra_counter == 1
    e.tick(NONE)                                   # reload
    ev = e.tick(RIGHT)
    assert EventKind.EXTRA_LIFE in kinds(ev)
    assert e.state.lives == 4 and e.state.extra_counter == 2


# ---------------------------------------------------------------- T9
def test_t9_blast_destroys_heart_without_decrement_and_destroys_exit():
    e = Engine([room('% @ %', '%   %', '%$&!%')])
    assert e.state.hearts_left == 1
    run(e, 3)
    assert e.grid[idx(1, 2)] == C.ANIM0 and e.grid[idx(3, 2)] == C.ANIM0
    assert e.state.hearts_left == 1
    run(e, 6)
    assert e.grid[idx(1, 2)] == C.ANIM6
    run(e, 1)
    assert e.grid[idx(1, 2)] == C.EMPTY and e.grid[idx(3, 2)] == C.EMPTY


# ---------------------------------------------------------------- T10
def test_t10_bomb_lands_softly_on_grass():
    e = Engine([room('%&%', '% %', '% %', '%.%')])
    run(e, 1)
    assert e.grid[idx(1, 0)] == C.BOMB_WAKING
    run(e, 2)
    assert e.grid[idx(1, 2)] == C.BOMB_FALLING
    ev = run(e, 1)
    assert e.grid[idx(1, 2)] == C.BOMB and EventKind.BOMB_LANDED in kinds(ev)
    run(e, 3)
    assert C.BLAST not in e.grid and C.ANIM0 not in e.grid


@pytest.mark.parametrize('floor', ['%', '@'])
def test_t10_bomb_explodes_next_tick_on_anything_else(floor):
    e = Engine([room('%&%', '% %', '% %', f'%{floor}%')])
    run(e, 4)
    assert e.grid[idx(1, 2)] == C.BLAST
    ev = run(e, 1)
    assert EventKind.BLAST in kinds(ev)
    assert e.grid[idx(1, 2)] == C.ANIM0 and e.grid[idx(1, 1)] == C.ANIM0
    assert e.grid[idx(1, 3)] == (C.HARD_WALL if floor == '%' else C.ANIM0)


def test_t10_bomb_on_hero_explodes_same_tick():
    e = Engine([room('%&%', '% %', '%*%', hero=False)])
    run(e, 2)
    assert e.grid[idx(1, 1)] == C.BOMB_FALLING
    ev = run(e, 1)
    assert EventKind.HERO_DIED in kinds(ev)
    assert e.grid[idx(1, 2)] == C.ANIM0 and e.grid[idx(1, 1)] == C.ANIM0


# ---------------------------------------------------------------- T11
def test_t11_two_heroes_move_together():
    e = Engine([room('%*  %', '%*  %', hero=False)])
    e.tick(RIGHT)
    assert e.grid[idx(2, 0)] == C.HERO and e.grid[idx(2, 1)] == C.HERO
    assert e.grid[idx(1, 0)] == C.EMPTY and e.grid[idx(1, 1)] == C.EMPTY


def test_t11_game_continues_while_one_hero_lives():
    e = Engine([room('%@% %', '% % %', '%*%*%', hero=False)])
    ev = run(e, 3)
    assert EventKind.BLAST in kinds(ev) and EventKind.HERO_DIED not in kinds(ev)
    assert e.state.status is Status.PLAYING
    assert e.grid[idx(3, 2)] == C.HERO


def test_t11_both_dead_is_death():
    e = Engine([room('%@%@%', '% % %', '%*%*%', hero=False)])
    ev = run(e, 3)
    assert EventKind.HERO_DIED in kinds(ev)


def test_t11_any_hero_entering_exit_completes_room():
    e = Engine([room('%* !%', '%*%%%', hero=False)])
    run(e, 2, RIGHT)
    assert e.state.room_done
    assert e.grid[idx(1, 1)] == C.HERO


# ---------------------------------------------------------------- T12
def test_t12_three_lives_give_four_attempts():
    e = Engine([room('%@%', '% %', '%*%', hero=False)], lives=3)
    for attempt in range(4):
        for _ in range(6):
            if EventKind.HERO_DIED in kinds(e.tick(NONE)):
                break
        else:
            pytest.fail(f'attempt {attempt}: hero did not die')
        assert e.state.status is Status.DYING
        ev = run(e, DEATH_TICKS)
        if attempt < 3:
            assert e.state.lives == 2 - attempt and e.state.status is Status.PLAYING
            assert EventKind.ROOM_LOADED in kinds(e.tick(NONE))   # pristine reload
            assert e.grid[idx(1, 2)] == C.HERO
        else:
            assert EventKind.GAME_OVER in kinds(ev)
            assert e.state.status is Status.GAME_OVER
    assert e.tick(RIGHT) == []


# ---------------------------------------------------------------- T13
ROOM_ALPHABET = ' %#@$*!&.'
room_strategy = st.text(alphabet=ROOM_ALPHABET, min_size=240, max_size=240)
inputs_strategy = st.lists(st.sampled_from(list(Input)), min_size=1, max_size=60)


@settings(max_examples=200, deadline=None)
@given(room_strategy, inputs_strategy)
def test_t13_deterministic_and_well_formed(rm, inputs):
    a, b = Engine([rm]), Engine([rm])
    hero_count = a.grid.count(C.HERO)
    for inp in inputs:
        ea, eb = a.tick(inp), b.tick(inp)
        assert ea == eb
        assert a.grid == b.grid and a.state == b.state
        assert all(isinstance(c, Cell) for c in a.grid)
        n = a.grid.count(C.HERO)
        assert n <= hero_count or a.state.status is Status.DYING or EventKind.ROOM_LOADED in kinds(ea)
        hero_count = n


# ---------------------------------------------------------------- real data
LEVELS = Path(__file__).resolve().parent.parent / 'levels.txt'


def test_parse_real_levels():
    rooms = parse_levels(LEVELS.read_text())
    assert len(rooms) == 12                     # 4 original rooms + "Komnaty do Heartlighta" (TA 2/91)
    assert [r.count('$') for r in rooms] == [12, 8, 6, 11, 20, 13, 5, 8, 14, 12, 10, 14]
    assert rooms[3].count('*') == 2 and rooms[5].count('*') == 4
    assert all(r.count('!') == 1 for r in rooms)
    e = Engine(rooms)
    assert e.state.hearts_left == 12
    assert e.grid.count(C.ROCK) == 31               # every '@' became ROCK


def test_real_rooms_survive_random_play():
    import random
    rooms = parse_levels(LEVELS.read_text())
    rnd = random.Random(1990)
    for start in range(4):
        e = Engine(rooms)
        e.room = start
        e._load_room()                              # noqa: SLF001 - jump straight to the room
        for _ in range(500):
            e.tick(rnd.choice(list(Input)))
        assert all(isinstance(c, Cell) for c in e.grid)


# ---------------------------------------------------------------- extras used by the renderer
def test_abort_room_is_suicide():
    e = Engine([room('%*   *%', hero=False)])
    ev = e.abort_room()
    assert EventKind.HERO_DIED in kinds(ev) and e.state.status is Status.DYING
    assert e.grid[idx(1, 0)] == C.BLAST and e.grid[idx(5, 0)] == C.BLAST
    ev = e.tick(NONE)
    assert kinds(ev).count(EventKind.BLAST) == 2
    run(e, DEATH_TICKS - 1)
    assert e.state.lives == 2 and e.state.status is Status.PLAYING
    assert e.abort_room() == []                     # not while dying/loading


def test_start_room():
    rooms = parse_levels(LEVELS.read_text())
    e = Engine(rooms, start_room=3)
    assert e.state.room == 3 and e.grid.count(C.HERO) == 2
    with pytest.raises(ValueError):
        Engine(rooms, start_room=len(rooms))


def test_load_pending_and_explicit_load_room():
    e = Engine([room('%*!%', hero=False), room('%*%', hero=False)])
    assert not e.load_pending and e.load_room() == []
    e.tick(RIGHT)
    assert e.load_pending and e.state.room == 1
    assert e.grid[idx(1, 0)] == C.EMPTY                  # old room still shown
    ev = e.load_room()
    assert kinds(ev) == [EventKind.ROOM_LOADED] and not e.load_pending
    assert e.grid[idx(1, 0)] == C.HERO and e.grid[idx(2, 0)] == C.HARD_WALL
    assert EventKind.ROOM_LOADED not in kinds(e.tick(NONE))   # tick does not load twice


# ---------------------------------------------------------------- sound-relevant events
def test_events_for_sound_requests():
    # falling rock deflected off a resting rock: ROCK_ROLLED (LAND_SOUND fires on a roll too)
    e = Engine([room('% @ %', '%   %', '% @ %')])
    run(e, 2)                                            # wake, fall: now directly above the rock
    ev = run(e, 1)                                       # FALL_STEP -> MOVE_FALL rolls down-left
    assert EventKind.ROCK_ROLLED in kinds(ev) and e.grid[idx(1, 2)] == C.ROCK_FALLING
    # falling rock onto a bomb: ROCK_HIT the tick the blast is written
    e = Engine([room('%@%', '% %', '%&%')])
    ev = run(e, 3)
    assert EventKind.ROCK_HIT in kinds(ev) and EventKind.BLAST in kinds(ev)
    # falling heart onto the hero: HEART_HIT
    e = Engine([room('%$%', '% %', '%*%', hero=False)])
    ev = run(e, 3)                                       # wake in place, fall, hit
    assert EventKind.HEART_HIT in kinds(ev) and EventKind.HERO_DIED in kinds(ev)
    # bomb exploding on a hard floor: BOMB_HIT when its own cell becomes BLAST
    e = Engine([room('%&%', '% %')])
    ev = run(e, 3)
    assert EventKind.BOMB_HIT in kinds(ev) and e.grid[idx(1, 1)] == C.BLAST
    # blast animation frames report the frame they had, 0..6, then the cell is empty
    ev = run(e, 1)
    assert EventKind.BLAST in kinds(ev)
    frames = []
    for _ in range(8):
        ev = run(e, 1)
        frames.append(sorted({x.value for x in ev if x.kind is EventKind.BLAST_FRAME}))
    assert frames == [[0], [1], [2], [3], [4], [5], [6], []]


def test_default_initial_tick_is_the_loader_checksum_residue():
    """$D0 holds the last hex line's checksum ($4B, odd) when PLAY starts: no push on tick 1."""
    e = Engine([room('%*@ %', hero=False)])
    assert e.state.tick == 0x4B
    e.tick(RIGHT)
    assert e.grid[idx(1, 0)] == C.HERO and e.grid[idx(2, 0)] == C.ROCK
    e.tick(RIGHT)
    assert e.grid[idx(2, 0)] == C.HERO and e.grid[idx(3, 0)] == C.ROCK
    e = Engine([room('%*%', hero=False)], initial_tick=0xFF)
    e.tick(NONE)
    assert e.state.tick == 0                                    # one-byte counter wraps
