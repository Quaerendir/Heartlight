"""Play Heartlight: python -m heartlight.play [--scale N] [--room N] [--no-sound] [--os-font FILE]

Title screen: START/SHIFT/FIRE in the original = Enter, Space, Shift or a joystick
button here. In game: arrows / WASD / the original  - = + *  (up down left right),
ESC gives the room up (as in the original), Q or window close quits. Game over
returns to the title screen. --os-font takes a 1 KB Atari charset dump or an OS ROM
image for a pixel-exact title screen; without it a system font stands in.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from enum import Enum
from pathlib import Path

import pygame

from .engine import ROOM_W, Cell, Engine, Input, Status, parse_levels
from .render import (FPS, FRAMES_PER_TICK, Curtain, Renderer, Sounds, TextFont, TileState,
                     TitleScreen, load_os_font, load_rom, parse_title_banner)

ROOT = Path(__file__).resolve().parent.parent

KEYMAP: dict[int, Input] = {
    pygame.K_UP: Input.UP, pygame.K_DOWN: Input.DOWN, pygame.K_LEFT: Input.LEFT, pygame.K_RIGHT: Input.RIGHT,
    pygame.K_w: Input.UP, pygame.K_s: Input.DOWN, pygame.K_a: Input.LEFT, pygame.K_d: Input.RIGHT,
    pygame.K_MINUS: Input.UP, pygame.K_EQUALS: Input.DOWN,                       # original: - = + *
    pygame.K_PLUS: Input.LEFT, pygame.K_KP_PLUS: Input.LEFT, pygame.K_ASTERISK: Input.RIGHT,
    pygame.K_KP_MULTIPLY: Input.RIGHT, pygame.K_KP8: Input.UP, pygame.K_KP2: Input.DOWN,
    pygame.K_KP4: Input.LEFT, pygame.K_KP6: Input.RIGHT,
}
START_KEYS = {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT}


class Screen(Enum):
    TITLE = 'title'
    CURTAIN = 'curtain'
    PLAY = 'play'


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
    ap.add_argument('--no-title', action='store_true', help='skip the title screen')
    ap.add_argument('--os-font', type=Path, default=os.environ.get('HEARTLIGHT_OS_FONT'),
                    help='Atari OS charset (1 KB) or OS ROM image, for the title screen')
    ap.add_argument('--data', type=Path, default=ROOT, help='directory with game.bin, meta.json, levels.txt')
    args = ap.parse_args(argv)

    rom = load_rom(args.data / 'game.bin', args.data / 'meta.json')
    meta = json.loads((args.data / 'meta.json').read_text())
    lives = meta['lives'] if args.lives is None else args.lives
    extra = meta['extra'] if args.extra is None else args.extra
    levels_text = (args.data / 'levels.txt').read_text()
    rooms = parse_levels(levels_text)
    os_font = load_os_font(args.os_font) if args.os_font else None

    pygame.init()
    renderer = Renderer(rom, args.scale)
    screen = pygame.display.set_mode(renderer.size)
    pygame.display.set_caption('HEARTLIGHT - Janusz Pelc 1990')
    title = TitleScreen(rom, parse_title_banner(levels_text), renderer, TextFont(args.scale, os_font))
    sounds = Sounds(enabled=not args.no_sound)
    pygame.joystick.init()
    joystick = pygame.joystick.Joystick(0) if pygame.joystick.get_count() else None
    clock = pygame.time.Clock()

    engine: Engine | None = None
    tiles = TileState(dict(rom.tile_tab))
    curtain: Curtain | None = None
    shown: list[int] = [Cell.EMPTY] * (ROOM_W * 12)      # CLR_GRID: the first curtain starts from blank
    mode = Screen.TITLE
    frame = 0

    def start_game() -> None:
        nonlocal engine, tiles, curtain, mode
        engine = Engine(rooms, lives=lives, extra=extra, start_room=args.room - 1)
        tiles = TileState(dict(rom.tile_tab))
        tiles.on_room_loaded()
        curtain = Curtain(shown, engine.grid)
        mode = Screen.CURTAIN

    if args.no_title:
        start_game()

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_q):
                pygame.quit()
                return 0
            if mode is Screen.TITLE and (ev.type == pygame.JOYBUTTONDOWN or
                                         (ev.type == pygame.KEYDOWN and ev.key in START_KEYS)):
                start_game()
            elif mode is Screen.PLAY and engine is not None and ev.type == pygame.KEYDOWN \
                    and ev.key == pygame.K_ESCAPE:
                sounds.play(engine.abort_room())

        if mode is Screen.TITLE:
            title.draw(screen)
        elif mode is Screen.CURTAIN and curtain is not None and engine is not None:
            curtain.step()
            sounds.curtain_blip()
            renderer.draw_status(screen, engine.state.lives, engine.state.room)
            renderer.draw_grid(screen, curtain.cells, tiles)
            if not curtain.running:
                mode, frame = Screen.PLAY, 0
        elif mode is Screen.PLAY and engine is not None:
            if engine.load_pending:                              # win or death: LOAD_ROOM with curtain
                previous = list(shown)
                engine.load_room()
                tiles.on_room_loaded()
                curtain = Curtain(previous, engine.grid)
                mode = Screen.CURTAIN
                continue
            if frame % FRAMES_PER_TICK == 0:
                inp = read_input(joystick)
                tick_before = engine.state.tick
                events = engine.tick(inp)
                tiles.after_tick(inp, tick_before, engine.state.hearts_left)
                sounds.play(events)
                if engine.state.status is Status.GAME_OVER:      # JMP PLAY: back to the title
                    mode = Screen.TITLE
            shown = [int(c) for c in engine.grid]
            renderer.draw(screen, engine, tiles)
        pygame.display.flip()
        clock.tick(FPS)
        frame += 1


if __name__ == '__main__':
    sys.exit(main())
