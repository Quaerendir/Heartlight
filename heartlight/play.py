"""Play Heartlight: python -m heartlight.play [--scale N] [--room N] [--no-sound]

Keys: arrows / WASD / the original  - = + *  (up down left right), ESC = give up
the room (as in the original), Q or window close = quit. Joystick: hat or axes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pygame

from .engine import Engine, EventKind, Input, Status, parse_levels
from .render import FPS, FRAMES_PER_TICK, Renderer, Sounds, TileState, load_rom

ROOT = Path(__file__).resolve().parent.parent

KEYMAP: dict[int, Input] = {
    pygame.K_UP: Input.UP, pygame.K_DOWN: Input.DOWN, pygame.K_LEFT: Input.LEFT, pygame.K_RIGHT: Input.RIGHT,
    pygame.K_w: Input.UP, pygame.K_s: Input.DOWN, pygame.K_a: Input.LEFT, pygame.K_d: Input.RIGHT,
    pygame.K_MINUS: Input.UP, pygame.K_EQUALS: Input.DOWN,                       # original: - = + *
    pygame.K_PLUS: Input.LEFT, pygame.K_KP_PLUS: Input.LEFT, pygame.K_ASTERISK: Input.RIGHT,
    pygame.K_KP_MULTIPLY: Input.RIGHT, pygame.K_KP8: Input.UP, pygame.K_KP2: Input.DOWN,
    pygame.K_KP4: Input.LEFT, pygame.K_KP6: Input.RIGHT,
}


def read_input(joystick: pygame.joystick.JoystickType | None) -> Input:
    if joystick is not None:
        hx, hy = joystick.get_hat(0) if joystick.get_numhats() else (0, 0)
        ax = joystick.get_axis(0) if joystick.get_numaxes() > 1 else 0.0
        ay = joystick.get_axis(1) if joystick.get_numaxes() > 1 else 0.0
        if hy > 0 or ay < -0.5:
            return Input.UP
        if hy < 0 or ay > 0.5:
            return Input.DOWN
        if hx < 0 or ax < -0.5:
            return Input.LEFT
        if hx > 0 or ax > 0.5:
            return Input.RIGHT
    keys = pygame.key.get_pressed()
    for key, inp in KEYMAP.items():
        if keys[key]:
            return inp
    return Input.NONE


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Heartlight (Atari 8-bit, 1990) - pygame front end')
    ap.add_argument('--scale', type=int, default=3)
    ap.add_argument('--room', type=int, default=1, help='start room, 1-based')
    ap.add_argument('--lives', type=int, default=None)
    ap.add_argument('--extra', type=int, default=None)
    ap.add_argument('--no-sound', action='store_true')
    ap.add_argument('--data', type=Path, default=ROOT, help='directory with game.bin, meta.json, levels.txt')
    args = ap.parse_args(argv)

    rom = load_rom(args.data / 'game.bin', args.data / 'meta.json')
    import json
    meta = json.loads((args.data / 'meta.json').read_text())
    lives = meta['lives'] if args.lives is None else args.lives
    extra = meta['extra'] if args.extra is None else args.extra
    rooms = parse_levels((args.data / 'levels.txt').read_text())

    pygame.init()
    renderer = Renderer(rom, args.scale)
    screen = pygame.display.set_mode(renderer.size)
    pygame.display.set_caption('HEARTLIGHT - Janusz Pelc 1990')
    sounds = Sounds(enabled=not args.no_sound)
    pygame.joystick.init()
    joystick = pygame.joystick.Joystick(0) if pygame.joystick.get_count() else None
    clock = pygame.time.Clock()

    def new_game() -> tuple[Engine, TileState]:
        return Engine(rooms, lives=lives, extra=extra, start_room=args.room - 1), TileState(dict(rom.tile_tab))

    engine, tiles = new_game()
    frame = 0
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_q):
                pygame.quit()
                return 0
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                sounds.play(engine.abort_room())
            if engine.state.status is Status.GAME_OVER and (
                    ev.type == pygame.KEYDOWN or ev.type == pygame.JOYBUTTONDOWN):
                engine, tiles = new_game()
        if frame % FRAMES_PER_TICK == 0 and engine.state.status is not Status.GAME_OVER:
            inp = read_input(joystick)
            tick_before = engine.state.tick
            events = engine.tick(inp)
            if any(e.kind is EventKind.ROOM_LOADED for e in events):
                tiles.on_room_loaded()
            tiles.after_tick(inp, tick_before, engine.state.hearts_left)
            sounds.play(events)
        renderer.draw(screen, engine, tiles)
        pygame.display.flip()
        clock.tick(FPS)
        frame += 1


if __name__ == '__main__':
    sys.exit(main())
