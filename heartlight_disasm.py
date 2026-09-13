#!/usr/bin/env python3
"""Annotated recursive-descent 6502 disassembly of Heartlight game.bin (py65)."""
import sys
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

LOAD, ENTRY = 0x9014, 0x9260
data = open(sys.argv[1], 'rb').read()
END = LOAD + len(data)
mpu = MPU()
for i, b in enumerate(data): mpu.memory[LOAD + i] = b
dis = Disassembler(mpu)

NAMES = {
 0x9260:'PLAY', 0x9269:'DL_GAME', 0x928B:'DL_TITLE', 0x92A4:'STATUS_LINE', 0x92CC:'TITLE_TEXT',
 0x9308:'ROOM_START', 0x930B:'MAIN_LOOP', 0x931E:'CHK_ROOM_DONE', 0x932A:'HERO_DEAD', 0x9342:'DEATH_WAIT',
 0x9357:'RELOAD_ROOM', 0x935D:'ROOM_DONE', 0x9370:'ROOM_BCD_INC', 0x938A:'SHOW_LIVES2', 0x938D:'RESET_EXTRA',
 0x9396:'SHOW_LIVES', 0x93A0:'BCD_LOOP', 0x93B2:'RTS1',
 0x93B3:'H_ROCK', 0x93B8:'H_ROCK_WAKE', 0x93BF:'H_ROCK_FALL', 0x93C9:'H_HEART', 0x93CE:'H_HEART_FALL',
 0x93D6:'FALL_STEP', 0x93ED:'HIT_DETONATE', 0x93F2:'LAND_SOUND', 0x93F7:'FALL_MOVE',
 0x9402:'H_BOMB', 0x9407:'H_BOMB_WAKE', 0x940E:'H_BOMB_FALL', 0x9426:'BF_LANDED', 0x942E:'BF_EXPLODE', 0x9430:'BF_STORE', 0x9434:'BF_CONTINUE',
 0x943B:'H_BLAST', 0x943D:'BL_LOOP', 0x9450:'BL_CHAIN', 0x9454:'BL_DESTROY', 0x9456:'BL_STORE', 0x9459:'BL_NEXT', 0x9463:'RTS2',
 0x9464:'H_EXIT', 0x9478:'EX_STORE',
 0x947C:'H_HERO', 0x948E:'HERO_KBD', 0x949B:'HERO_MATCH', 0x949D:'HM_LOOP', 0x94A5:'HERO_IDLE', 0x94AE:'HERO_MOVE', 0x94D0:'HERO_TRY', 0x94DA:'HERO_STEP', 0x94E7:'RTS3',
 0x94E8:'PUSH', 0x9509:'PUSH_CHK', 0x952B:'PUSH_END', 0x952E:'ENTER_CELL', 0x953C:'EC_GRASS', 0x9547:'EC_EXIT', 0x955A:'EC_BLOCKED',
 0x955C:'KEYTAB', 0x956C:'REST_CHECK', 0x959C:'RC_RIGHT', 0x95AA:'RTS4', 0x95AB:'RC_WAKE',
 0x95B1:'MOVE_FALL', 0x95C5:'MF_ROLL', 0x95C6:'MF_PUT', 0x95CC:'MF_BLOCKED', 0x95E2:'MF_RIGHT', 0x95F0:'MF_REST',
 0x95F7:'PROBE', 0x9601:'PR_OUT', 0x9604:'PR_Y', 0x961F:'RTS5', 0x9620:'DX_TAB', 0x9626:'DY_TAB', 0x962C:'DIDX_TAB',
 0x9632:'SND_REQ', 0x963A:'RTS6', 0x963B:'SND_PLAY', 0x966F:'RTS7', 0x9670:'SND_F', 0x9672:'SND_F2', 0x9674:'SND_C',
 0x9678:'SCAN', 0x9685:'SC_CELL', 0x96A1:'SC_ANIM_PUT', 0x96A6:'SC_DISPATCH', 0x96BA:'DISPATCH_JSR', 0x96BF:'SC_NEXT', 0x96CD:'SC_INX',
 0x96D4:'CLR_MOVED', 0x96F0:'HERO_ANIM0', 0x96F2:'HERO_ANIM_PUT', 0x970B:'TICK_END', 0x9717:'WAIT_TICK',
 0x9723:'RENDER', 0x972D:'RN_ROW', 0x9731:'RN_CELL', 0x9756:'RN_NEXT', 0x9766:'RN_ROW_END',
 0x9777:'PUT_BCD', 0x9780:'PUT_DIGIT', 0x978A:'TITLE_INIT', 0x9795:'WAIT_START', 0x97B5:'CLR_GRID', 0x97D5:'SET_DISPLAY', 0x97E8:'TITLE_CONV', 0x97FC:'TC_PUT',
 0x980C:'WAIT_VBL', 0x980E:'WV_LOOP', 0x9813:'LOAD_ROOM', 0x9820:'LR_ADD240', 0x982B:'LR_DEX', 0x982E:'LR_CURTAIN',
 0x9854:'CURTAIN', 0x9859:'CU_ROUND', 0x985D:'CU_RND', 0x9874:'CU_FILL', 0x987C:'CURTAIN_FRAME', 0x9897:'PUT_CELL', 0x98A0:'PC_RANGE', 0x98A8:'PC_ROCK', 0x98AA:'PC_STORE',
 0x98AE:'CURTAIN_MODE', 0x98AF:'COUNT_CELLS', 0x98B3:'CC_LOOP', 0x98B9:'CC_NEXT',
 0x98C0:'LIVES', 0x98C1:'LIVES_BCD', 0x98C2:'HEARTS_LEFT', 0x98C3:'ROOM', 0x98C4:'ROOM_BCD', 0x98C5:'LAST_DIR', 0x98C6:'ROOM_DONE_FLAG', 0x98C7:'SND_PRI', 0x98C8:'EXTRA_CTR',
 0x98C9:'TILE_TAB', 0x98CA:'TILE_EXIT', 0x98CD:'TILE_HEART', 0x98D2:'TILE_HEART_F', 0x98D3:'TILE_HERO', 0x98E0:'HANDLER_TAB', 0x98E1:'HANDLER_TAB_HI',
 0x9EC0:'GRID', 0x9B00:'SCREEN', 0x9FC0:'TITLE_LINE', 0x9000:'CHARSET',
 0x7000:'P_LIVES', 0x7001:'P_EXTRA', 0x7002:'P_ROOMS', 0x7003:'P_TITLE',
 0xD300:'PORTA', 0xD20F:'SKSTAT', 0xD209:'KBCODE', 0xD21A:'RANDOM', 0xD200:'AUDF1', 0xD201:'AUDC1', 0xD400:'DMACTL',
 0xD01F:'CONSOL', 0xD010:'TRIG0', 0xD011:'TRIG1', 0x021C:'CDTMV2', 0x021E:'CDTMV3', 0x022F:'SDMCTL', 0x0230:'SDLSTL', 0x0231:'SDLSTH',
 0x02F4:'CHBAS', 0x02FC:'CH', 0xFB51:'OS_KEYTAB',
}
ZP = {0x00:'CX', 0x01:'CY', 0xCB:'PTR', 0xCC:'PTR+1', 0xCD:'TMP', 0xCE:'TMP2', 0xD0:'TICK', 0x11:'BRKKEY', 0x14:'RTCLOK', 0x4D:'ATRACT'}

C = {  # comments
 0x9260:'entry from BASIC USR(PLAY)', 0x9263:'title screen, wait for START/SHIFT/fire, init game',
 0x9308:'load room ROOM, count hearts', 0x930B:'one physics tick (all objects incl. hero)',
 0x930E:'key pressed?', 0x931A:'ESC = suicide', 0x931E:'bit7 clear => room completed',
 0x9323:'count hero cells (\'*\')', 0x9328:'hero alive => next tick', 0x932A:'turn every hero into a blast (ESC)',
 0x933D:'wait 64 frames while ticking (death animation)', 0x934A:'lives-1; 0 is still playable, wrap to $FF = game over',
 0x9354:'game over -> title', 0x935D:'next room; wrap to room 0 after last (game never ends)',
 0x937B:'every P_EXTRA rooms: bonus life', 0x9396:'LIVES -> BCD in LIVES_BCD (cap 99)',
 0x93B3:"rock at rest ($27 '\\''): may wake into $2F", 0x93B8:"rock waking ($2F '/'): first move, becomes $28",
 0x93BF:"rock falling ($28 '('): landing kills hero / detonates bombs", 0x93C9:"heart at rest ($24 '$'): wakes DIRECTLY into $29 (no wake state)",
 0x93CE:"heart falling ($29 ')')", 0x93D6:'A=falling code, Y=rest code; probe cell below',
 0x93DF:'below empty -> keep falling', 0x93E1:'below = hero -> hero cell becomes blast', 0x93E5:'below = falling bomb', 0x93E9:'below = bomb at rest',
 0x93ED:"write '+' (blast next tick) into cell below", 0x93F7:'move/roll/land via MOVE_FALL',
 0x9402:"bomb at rest ($26 '&'): may wake into $2D", 0x9407:"bomb waking ($2D '-')", 0x940E:"bomb falling ($22 '\"')",
 0x9413:'below empty -> keep falling', 0x941C:'below = hero -> hero explodes, bomb stays', 0x9426:"below = grass -> lands softly, back to '&'",
 0x942E:'anything else below (rock, wall, border...) -> bomb becomes blast',
 0x943B:"blast ($2B '+'): 4 orthogonal neighbours only (dirs 3..0 = down,up,right,left)", 0x9442:'out of grid', 0x9444:"hard wall '%' survives",
 0x9448:'bomb -> chained blast next tick', 0x944C:"'+' stays '+'", 0x9454:"everything else -> '0' (anim frame 0)", 0x945E:"centre -> '0'",
 0x9464:"exit ('!'): blink tile when HEARTS_LEFT==0", 0x947C:'hero: joystick 1&2 (active low) else keyboard',
 0x9483:'merge both sticks', 0x948E:'SKSTAT bit2: key down?', 0x9495:'KBCODE -> ATASCII via OS table',
 0x949B:'match against KEYTAB (16 entries, index&3 = dir)', 0x94A5:'no input: clear walk animation bits',
 0x94AE:'dir: 0=left 1=right 2=up 3=down', 0x94B5:'push only for left/right', 0x94B9:'facing bits in TILE_HERO',
 0x94D0:'target empty?', 0x94D5:'try heart/grass/exit', 0x94DA:'move hero (set bit7 = moved)',
 0x94E8:'PUSH: cell beyond must be in grid', 0x94F4:'x+2*dx >= 20 -> fail', 0x94FF:"only rock at rest ('\\'')", 0x9505:"or bomb at rest ('&')",
 0x950F:'cell beyond object must be empty', 0x9514:'push allowed on EVEN ticks only', 0x951E:'move object (keeps rest code, bit7 set)',
 0x952E:"'$' heart: HEARTS_LEFT-1, enter", 0x953C:"'.' grass: enter", 0x9547:"'!' exit: only when HEARTS_LEFT==0", 0x9550:'ROOM_DONE_FLAG=0 (bit7 clear = done)',
 0x955A:'blocked', 0x955C:'joystick nibbles L,R,U,D; then keys o p q a; + * - =; 6 9 8 7',
 0x956C:'REST_CHECK: A=wake code. Object at rest decides whether to wake', 0x9573:"below '.': stay", 0x9579:"below '%': stay", 0x957F:"below '*' hero: stay",
 0x9583:'below empty -> wake (no move this tick)', 0x9585:'cell above holds same wake code -> stay', 0x958E:'left empty AND down-left empty -> wake (roll)',
 0x959C:'right empty AND down-right empty -> wake (roll)', 0x95AB:'store wake code in place (no bit7)',
 0x95B1:'MOVE_FALL: A=falling code, Y=rest code. Clears own cell first', 0x95BC:'below empty -> move down', 0x95CC:"below '.' or '%' -> rest",
 0x95D4:'down-left AND left empty -> move DIAGONALLY down-left (one tick)', 0x95E2:'else down-right AND right empty -> diagonal down-right', 0x95F0:'else rest in place, C=1',
 0x95F7:'PROBE: Y=dir (0..5). Out of grid -> A=$FF,C=1 (solid border). Else A=cell&$7F, Y=index, C=occupied',
 0x9620:'dx: L R U D DL DR', 0x9626:'dy', 0x962C:'index delta: -1 +1 -20 +20 +19 +21',
 0x9678:'SCAN: X=0..239 TOP-DOWN, LEFT-TO-RIGHT. bit7 = moved this tick -> skip',
 0x968A:"values >= $30 are blast anim frames '0'..'6': advance, '7' -> space", 0x96A6:'low nibble -> HANDLER_TAB (self-modifying JSR)',
 0x96D2:'clear moved bits', 0x96F5:'heart tiles blink every tick', 0x9717:'wait CDTMV2 == 0', 0x971C:'6 frames per tick',
 0x9723:'RENDER: each cell = 2x2 chars from TILE_TAB[cell]', 0x976A:'status: lives at +9, room at +$23',
 0x978A:'title screen', 0x9795:'wait: START (CONSOL) or SHIFT (SKSTAT bit3) or TRIG0/1', 0x97BD:'LIVES from P_LIVES', 0x97C6:'EXTRA_CTR from P_EXTRA',
 0x97CF:'game display list, CHBAS=$90', 0x97E8:'zero CHARSET[0..19]; title ATASCII->screen code into TITLE_LINE',
 0x9813:'src = P_TITLE+20 + ROOM*240', 0x982E:'curtain of \'#\' then reveal', 0x9846:"HEARTS_LEFT = count('$')",
 0x9897:"PUT_CELL: chars outside $20..$2F become rock ('@' -> $27)", 0x98AF:'COUNT_CELLS: X = number of cells == A',
 0x98C9:'TILE_TAB[$20..$36]: tile base char per cell code (bit7 = colour)', 0x98E0:'HANDLER_TAB: 16 words indexed by cell low nibble',
}

code, labels, queue = {}, {}, [ENTRY] + [int(a, 16) for a in sys.argv[2:]]
BR = {0x10,0x30,0x50,0x70,0x90,0xB0,0xD0,0xF0}
def tgt(t):
    p = t.split()
    return int(p[1][1:], 16) if len(p) > 1 and p[1].startswith('$') and len(p[1]) == 5 else None
seen = set()
while queue:
    pc = queue.pop()
    while LOAD <= pc < END and pc not in seen:
        n, t = dis.instruction_at(pc); op = mpu.memory[pc]; m = t.split()[0]
        if m == 'BRK' or t.startswith('???'): break
        seen.add(pc); code[pc] = (n, t)
        if op in BR:
            a = tgt(t); labels.setdefault(a, f'L{a:04X}'); queue.append(a); pc += n
        elif m == 'JMP':
            if '(' in t: break
            a = tgt(t); labels.setdefault(a, f'L{a:04X}'); queue.append(a); break
        elif m == 'JSR':
            a = tgt(t); labels.setdefault(a, f'S{a:04X}'); queue.append(a); pc += n
        elif m in ('RTS', 'RTI'): break
        else: pc += n
for pc, (n, t) in code.items():
    p = t.split()
    if len(p) > 1:
        a = p[1].split(',')[0].strip('()')
        if a.startswith('$') and len(a) == 5:
            v = int(a[1:], 16)
            if LOAD <= v < END: labels.setdefault(v, f'D{v:04X}')
labels.update(NAMES)

def sym(arg):
    import re
    def r4(m):
        v = int(m.group(1), 16); return labels.get(v, m.group(0))
    def r2(m):
        v = int(m.group(1), 16); return ZP.get(v, m.group(0))
    arg = re.sub(r'\$([0-9a-fA-F]{4})', r4, arg)
    return re.sub(r'(?<![0-9a-fA-F#])\$([0-9a-fA-F]{2})(?![0-9a-fA-F])', r2, arg)

out = [f'; Heartlight (J. Pelc 1990) - game.bin  load ${LOAD:04X}-${END-1:04X}  entry PLAY=${ENTRY:04X}',
 '; Disassembled with py65 (recursive descent from PLAY + HANDLER_TAB entries). Unreached bytes = data.',
 '; Memory: CHARSET $9000 (bin starts at char 2 row 4), GRID $9EC0 (20x12, index=y*20+x, bit7=moved),',
 ';         SCREEN $9B00 (ANTIC mode 4, 2x2 chars per cell), room source P_TITLE+20 = $7017 + room*240.',
 '; Cell codes (ATASCII): $20 empty  $21 ! exit  $22 " bomb falling  $23 # soft wall  $24 $ heart  $25 % hard wall',
 ";         $26 & bomb  $27 ' rock (loader maps '@' here)  $28 ( rock falling  $29 ) heart falling  $2A * hero",
 ";         $2B + blast  $2D - bomb waking  $2E . grass  $2F / rock waking  $30-$36 blast anim frames -> $20",
 '; ZP: $00 CX $01 CY $CB/CC PTR $CD/CE TMP $D0 TICK', '']
pc = LOAD
while pc < END:
    if pc in code:
        n, t = code[pc]; raw = ' '.join(f'{mpu.memory[pc+i]:02X}' for i in range(n))
        p = t.split(None, 1); txt = f'{p[0]:<4}{sym(p[1])}' if len(p) == 2 else p[0]
        line = f'{pc:04X}  {raw:<9} {labels.get(pc, ""):<15} {txt:<22}'
        if pc in C: line += f'; {C[pc]}'
        out.append(line.rstrip()); pc += n
    else:
        s = pc; row = []
        while pc < END and pc not in code and len(row) < 8:
            if pc in labels and row: break
            row.append(mpu.memory[pc]); pc += 1
            if (pc in labels): break
        h = ' '.join(f'{b:02X}' for b in row); asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        line = f'{s:04X}  {"":<9} {labels.get(s, ""):<15} .byte {h:<24} ; {asc}'
        if s in C: line += f'  ; {C[s]}'
        out.append(line)
print('\n'.join(out))
print(f'; code bytes {sum(n for n,_ in code.values())}/{len(data)}', file=sys.stderr)
