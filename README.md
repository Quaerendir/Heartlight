# Heartlight (Atari 8-bit, 1990) — conversion pipeline

Clean reconstruction of Janusz Pelc's *Heartlight* as published in
**Tajemnice ATARI 1/91** (type-in listing). Goal: a faithful, deterministic
engine in Python and later a pygame front end.

Original game: Janusz Pelc, (C) 1990 Tajemnice ATARI. Rooms 5–12: Maciej
Mach, "Komnaty do Heartlighta", Tajemnice ATARI 2/91.
Conversion (extraction pipeline, disassembly, specification, engine and
pygame front end): **Quaerendir**.

## Files

| file | what |
|------|------|
| `1_91_heartlight.html` | the magazine article with the listing (UTF-8; source: unofficial TA archive, 2001) |
| `heartlight.bas` | the BASIC XL listing, identical to the article |
| `2_91_kody.html` | "Kody do Heartlighta i COS-u" (TA 2/91): the two-letter line codes printed for the listing; `tests/test_line_codes.py` checks all 313 lines of `heartlight.bas` against them |
| `2_91_hsvr.html`, `HEARTSVR.LST`, `SHORTHSV.LST` | "Heartlight Saver" (TA 2/91): the magazine's own tools to save the game as a standalone file; `build_xex.py --saver` reproduces the short one's file layout |
| `2_91_komnaty.html`, `KOMNATY.LST` | "Komnaty do Heartlighta" (TA 2/91): rooms 5–12 as DATA lines 1501–2212 to ENTER into the game; the LST is the file from the archive's `2_91.ATR`, identical to the article |
| `heartlight_extract.py` | stage 1: parses the listing, checksums the hex DATA, writes the files below |
| `levels.txt` | 12 rooms, 20×12 ASCII (`% # @ $ * ! & .`): the 4 original ones and the 8 of TA 2/91 |
| `meta.json` | colours, lives/extra/rooms, memory layout |
| `game.bin` | 6502 game code + charset, load `$9014`, entry `PLAY = $9260` |
| `loader.bin` | page-6 helper routines used only by the BASIC loader |
| `heartlight_disasm.py` | recursive-descent disassembler (needs `py65`) |
| `game.asm` | annotated disassembly of `game.bin` |
| `SPEC.md` | engine specification **v2**, every rule traced to a label in `game.asm` |
| `SPEC.v1.md` | earlier spec written from Boulder-Dash folklore, kept for the diff |
| `heartlight/engine.py` | stage 3: the engine, a literal re-implementation of the scan in `game.asm` |
| `tests/test_engine.py` | acceptance tests T1–T13 from `SPEC.md` §9 plus checks on the real rooms |
| `heartlight/render.py` | stage 4: charset from `game.bin`, GTIA palette, tile animation, POKEY channel emulation |
| `heartlight/play.py` | stage 4: the playable game (`heartlight` / `python -m heartlight.play`) |
| `heartlight/data/` | copies of `game.bin`, `meta.json`, `levels.txt` shipped inside the package |
| `docs/*.png` | screenshots rendered from the extracted data (title, curtain, rooms) |
| `tools/verify_timing.py` | runs the original loader and game code in py65 to confirm the timing constants |
| `tools/build_xex.py`, `heartlight.xex` | the game (12 rooms) as a standalone Atari binary for real hardware or emulators; `--saver` for the magazine's layout |
| `tools/line_codes.py` | the magazine's two-letter line codes ("Generator Kodów Kontrolnych", TA 2/91) for any listing |

## Usage

```
python3 heartlight_extract.py heartlight.bas --extra KOMNATY.LST --rooms 12   # -> levels.txt meta.json game.bin loader.bin
```
`--extra` merges the second listing by line number, as `ENTER "D:KOMNATY.LST"`
does, and `--rooms 12` is step 5 of the TA 2/91 instructions (the third
parameter of line 1050). Without them the outputs are the 4-room original.
```
pip install py65
python3 heartlight_disasm.py game.bin 9464 940E 93C9 9402 93B3 93BF 93CE 947C 943B 9407 93B8 > game.asm
```
The hex arguments are the jump-table entries at `$98E0` (object handlers),
which control-flow analysis cannot reach on its own.

```
pip install pytest hypothesis mypy
python3 -m pytest -q          # 62 tests
python3 -m mypy heartlight/   # strict
```

```
pip install heartlight            # from PyPI: engine + front end + game data
heartlight [--scale 3] [--room 1] [--no-sound]
```
or from a checkout: `pip install pygame-ce` and `python3 -m heartlight.play`.
Title screen: Enter, Space, Shift or a joystick button (START/SHIFT/FIRE in
the original). In game: arrows / WASD / the original `- = + *`, joystick hat
or stick; ESC gives the room up (as in the original), Q quits; game over
returns to the title. The screen is the original layout: a 40x24 ANTIC
mode-4 playfield with 2x2 characters per cell, the mode-5 status line (hero
icon, lives, room), the five colour registers from `meta.json`, 6 frames per
tick at 50 Hz, and the room-loading curtain (25 frames of random soft-wall
cells, then 25 frames revealing the room). The title screen texts come from
`game.bin` and the banner from the level data; the original draws them with
the Atari OS charset, which is not part of this repository. Pass
`--os-font FILE` (a 1 KB charset dump or an XL/OS-B ROM image) for a
pixel-exact title, otherwise a system font stands in.

![title](docs/title.png)

![room 1](docs/room1.png)

```python
from heartlight import Engine, Input, parse_levels
e = Engine(parse_levels(open('levels.txt').read()))
events = e.tick(Input.RIGHT)   # one physics scan; e.grid, e.state
```

## Back to the Atari: `heartlight.xex`

Tajemnice ATARI promised a tool to save the typed-in game as a standalone
file "without the BASIC part" in the next issue, and delivered it in TA 2/91
as "Heartlight Saver" (Mirosław Liminowicz): a long version writing tape and
disk boot formats and DOS files, and a short one writing DOS files only
(`HEARTSVR.LST`, `SHORTHSV.LST`; run the game, press RESET at the title,
run the saver). `tools/build_xex.py` writes `heartlight.xex` from the
extracted data instead: a DOS binary load file that recreates the memory
state the BASIC loader leaves behind (colour shadows 708–712, parameters and
rooms at `$7000`, code at `$9014`, `$D0` = `$4B`, RUNAD = `$9260`).
`--saver` writes the byte layout of the short saver instead (RUNAD, colours,
`$9000–$98FF`, level data); the two load to the same memory image except
that the magazine's tool leaves `$D0` alone and stops at `$98FF` (the eight
bytes beyond are zero padding), see `tests/test_timing_vs_original.py`.
Comparing them exposed a bug in the earlier `heartlight.xex`: the colours
went to 712–716 instead of 708–712 (fixed in 0.2.1). Load either file with
any DOS or XEX loader on an XL/XE or in an emulator. The py65 harness boots
the file the way DOS would and gets the same timeline as the BASIC-loaded
game. Keyboard control depends on the OS key table the game reads at
`$FB51`; the joystick works regardless.

```
python3 tools/build_xex.py            # -> heartlight.xex (5225 bytes, 12 rooms)
python3 tools/verify_timing.py --xex  # boot it in py65
```

## Memory map (from the BASIC loader, lines 230–240)

| address | content |
|---------|---------|
| `$0600` | loader routines (`loader.bin`) |
| `$7000` | lives, extra (rooms per bonus life), room count |
| `$7003` | title banner, 20 bytes |
| `$7017` | rooms, 240 bytes each, row-major |
| `$9000` | charset (first 20 bytes zeroed by the game), `game.bin` from `$9014` |
| `$9260` | `PLAY` entry |
| `$9B00` | screen (ANTIC mode 4) |
| `$9EC0` | 20×12 game grid |

## Listing verification

TA 2/91 printed the two-letter line codes for the Heartlight listing ("Kody
do Heartlighta i COS-u"). `tools/line_codes.py` implements the code
(recovered from the machine code of the magazine's "Generator Kodów
Kontrolnych": `Σ i·byte_i mod 676`, quotient and remainder by 26 as letters,
over the line as the E: editor returns it) and `tests/test_line_codes.py`
compares all 313 lines of `heartlight.bas` with the table: 311 agree; line
1060 is printed as `10` for `IO`, and line 11920 is printed `KC` for the
computed `KD` while the line's own hex checksum passes and no single-
character variant with a valid checksum gives `KC`, so the table is taken
to be wrong there.

## Status

Stage 1 done and verified (all 191 hex-line checksums pass, outputs reproduce
bit-for-bit). Stage 2 (disassembly) done. Stage 3 (engine) implemented and
tested against `SPEC.md`. Stage 4 (pygame) playable with title screen,
curtain and sound: `SND_REQ`/`SND_PLAY` are reproduced register for register
(priority per event, AUDF/AUDC tables, one PAL frame per blip, random pitch
for priority 3, blast frames getting louder) through a small POKEY channel
emulation (17/5/4-bit polynomial counters, 64 kHz divider). The timing
constants (11 scans of death sequence, tick counter starting at $4B, first
scan of a room without delay, 3 frames per curtain step) were confirmed by
running the original 6502 code in py65 (`tools/verify_timing.py`), which the
test suite repeats. Nothing in the reconstruction is guessed any more.

## License

The conversion (extractor, disassembler, engine, front end, tests, specs) is
released under the MIT licence, see `LICENSE`. The original game and the
material derived from it (`heartlight.bas`, the article, `game.bin`,
`levels.txt`, `game.asm`, screenshots) remain (C) 1990 Janusz Pelc /
Tajemnice ATARI and are included for preservation and study only, see
`NOTICE`.
