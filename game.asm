; Heartlight (J. Pelc 1990) - game.bin  load $9014-$9907  entry PLAY=$9260
; Disassembled with py65 (recursive descent from PLAY + HANDLER_TAB entries). Unreached bytes = data.
; Memory: CHARSET $9000 (bin starts at char 2 row 4), GRID $9EC0 (20x12, index=y*20+x, bit7=moved),
;         SCREEN $9B00 (ANTIC mode 4, 2x2 chars per cell), room source P_TITLE+20 = $7017 + room*240.
; Cell codes (ATASCII): $20 empty  $21 ! exit  $22 " bomb falling  $23 # soft wall  $24 $ heart  $25 % hard wall
;         $26 & bomb  $27 ' rock (loader maps '@' here)  $28 ( rock falling  $29 ) heart falling  $2A * hero
;         $2B + blast  $2D - bomb waking  $2E . grass  $2F / rock waking  $30-$36 blast anim frames -> $20
; ZP: $00 CX $01 CY $CB/CC PTR $CD/CE TMP $D0 TICK

9014                            .byte 01 06 0B 1F 00 00 00 00  ; ........
901C                            .byte 40 90 E0 F4 00 00 00 01  ; @.......
9024                            .byte 06 1B 2F 7F 00 00 00 40  ; ../....@
902C                            .byte 90 E4 F8 FD 00 01 06 1B  ; ........
9034                            .byte 2F 7F BF FF 00 40 90 E4  ; /....@..
903C                            .byte F8 FD FE FF 01 06 1B 2F  ; ......./
9044                            .byte 7F BF FF FF 40 90 E4 F8  ; ....@...
904C                            .byte FD FE FF FF 2A 20 21 22  ; ....* !"
9054                            .byte 21 22 15 00 AA 01 99 65  ; !".....e
905C                            .byte 99 65 55 00 00 01 06 0A  ; .eU.....
9064                            .byte 1A 2A 2A 2A 00 50 94 A4  ; .***.P..
906C                            .byte A5 A5 A5 A5 00 01 00 10  ; ........
9074                            .byte 00 01 00 10 00 04 00 00  ; ........
907C                            .byte 04 00 00 00 00 00 00 09  ; ........
9084                            .byte 00 2F 00 2F 00 00 00 24  ; ././...$
908C                            .byte 00 FD 00 FD 03 03 00 03  ; ........
9094                            .byte 0E 3A 19 34 F0 A8 89 52  ; .:.4...R
909C                            .byte 54 55 54 01 00 02 05 0D  ; TUT.....
90A4                            .byte 0B 3F 0F 0B 00 A8 6B 5A  ; .?....kZ
90AC                            .byte 55 54 E4 98 02 05 0D 0B  ; UT......
90B4                            .byte 3F 0F 0B 0A A8 6B 5A 55  ; ?....kZU
90BC                            .byte 54 E4 98 B4 00 0A 3A 29  ; T.....:)
90C4                            .byte 15 05 06 09 00 A0 54 5C  ; ......T\
90CC                            .byte 78 7F FC B8 0A 3A 29 15  ; x....:).
90D4                            .byte 05 06 09 07 A0 54 5C 78  ; .....T\x
90DC                            .byte 7F FC B8 A8 01 06 09 17  ; ........
90E4                            .byte 2F 2F 1F 2F 50 A4 58 F5  ; //./P.X.
90EC                            .byte FE FE FD FE 3F 3A 3A 3A  ; ....?:::
90F4                            .byte 3A 3A 15 00 FF A9 A9 A9  ; ::......
90FC                            .byte A9 A9 55 00 00 00 00 00  ; ..U.....
9104                            .byte 00 00 00 00 00 00 00 00  ; ........
910C                            .byte 00 00 00 00 1F 0B 06 01  ; ........
9114                            .byte 00 00 00 00 F4 E0 90 40  ; .......@
911C                            .byte 00 00 00 00 7F 2F 1B 06  ; ...../..
9124                            .byte 01 00 00 00 FD F8 E4 90  ; ........
912C                            .byte 40 00 00 00 FF BF 7F 2F  ; @....../
9134                            .byte 1B 06 01 00 FF FE FD F8  ; ........
913C                            .byte E4 90 40 00 FF FF BF 7F  ; ..@.....
9144                            .byte 2F 1B 06 01 FF FF FE FD  ; /.......
914C                            .byte F8 E4 90 40 AA 01 99 65  ; ...@...e
9154                            .byte 99 65 55 00 2A 20 21 22  ; .eU.* !"
915C                            .byte 21 22 15 00 2A 2A 1A 15  ; !"..**..
9164                            .byte 05 05 01 00 A5 95 95 55  ; .......U
916C                            .byte 54 54 50 00 00 00 00 04  ; TTP.....
9174                            .byte 00 00 10 00 41 00 00 10  ; ....A...
917C                            .byte 01 00 40 00 00 0B 00 02  ; ..@.....
9184                            .byte 00 00 00 00 00 F4 00 D0  ; ........
918C                            .byte 00 40 00 00 09 20 05 20  ; .@... . 
9194                            .byte 05 05 01 00 54 01 54 01  ; ....T.T.
919C                            .byte 54 54 50 00 0A 0A 09 01  ; TTP.....
91A4                            .byte 01 03 0F 00 B4 F4 D4 54  ; .......T
91AC                            .byte 58 BC FC 00 0A 09 31 3D  ; X.....1=
91B4                            .byte 0F 00 00 00 F4 D4 5B 5F  ; ......[_
91BC                            .byte 3C 00 00 00 07 07 05 05  ; <.......
91C4                            .byte 09 0F 0F 00 A8 E8 D8 50  ; .......P
91CC                            .byte 50 B0 FC 00 07 05 39 3D  ; P.....9=
91D4                            .byte 0F 00 00 00 E8 D8 53 5F  ; ......S_
91DC                            .byte 3C 00 00 00 2F 1F 2F 2F  ; <..././/
91E4                            .byte 25 1A 15 00 FE FD FE FE  ; %.......
91EC                            .byte 56 A9 55 00 FF A9 A9 A9  ; V.U.....
91F4                            .byte A9 A9 55 00 3F 3A 3A 3A  ; ..U.?:::
91FC                            .byte 3A 3A 15 00 54 A8 CC CC  ; ::..T...
9204                            .byte CC CC A8 54 10 60 B0 30  ; ...T.`.0
920C                            .byte 30 30 A8 54 54 A8 0C FC  ; 00.TT...
9214                            .byte C0 C0 A8 54 54 A8 0C 3C  ; ...TT..<
921C                            .byte 0C 0C A8 54 40 84 C8 CC  ; ...T@...
9224                            .byte FC 0C 08 04 54 A8 C0 FC  ; ....T...
922C                            .byte 0C 0C A8 54 54 A8 C0 FC  ; ...TT...
9234                            .byte CC CC A8 54 54 A8 0C 0C  ; ...TT...
923C                            .byte 0C 0C 08 04 54 A8 CC FC  ; ....T...
9244                            .byte CC CC A8 54 54 A8 CC FC  ; ...TT...
924C                            .byte 0C 0C A8 54 FF ED DD D5  ; ...T....
9254                            .byte F6 D5 DD FF FF 5B D7 F7  ; .....[..
925C                            .byte D7 DF 67 FF              ; ..g.
9260  A2 FF     PLAY            LDX #$ff              ; entry from BASIC USR(PLAY)
9262  9A                        TXS
9263  20 8A 97                  JSR TITLE_INIT        ; title screen, wait for START/SHIFT/fire, init game
9266  4C 08 93                  JMP ROOM_START
9269            DL_GAME         .byte 30 45 A4 92 30 44 00 9B  ; 0E..0D..
9271                            .byte 04 04 04 04 04 04 04 04  ; ........
9279                            .byte 04 04 04 04 04 04 04 04  ; ........
9281                            .byte 04 04 04 04 04 04 04 41  ; .......A
9289                            .byte 69 92                    ; i.
928B            DL_TITLE        .byte 70 70 70 70 70 70 70 70  ; pppppppp
9293                            .byte 47 CC 92 70 06 70 70 70  ; G..p.ppp
929B                            .byte 70 06 70 46 C0 9F 41 8B  ; p.pF..A.
92A3                            .byte 92                       ; .
92A4            STATUS_LINE     .byte 80 80 80 80 80 1A 1B 80  ; ........
92AC                            .byte C0 C4 80 80 80 80 80 80  ; ........
92B4                            .byte 80 80 80 80 80 80 80 80  ; ........
92BC                            .byte 80 80 80 80 80 80 80 4A  ; .......J
92C4                            .byte 4B 80 C0 C1 80 80 80 80  ; K.......
92CC            TITLE_TEXT      .byte 80 80 80 80 80 A8 A5 A1  ; ........
92D4                            .byte B2 B4 AC A9 A7 A8 B4 80  ; ........
92DC                            .byte 80 80 80 80 00 61 75 74  ; .....aut
92E4                            .byte 6F 72 5A 00 6A 61 6E 75  ; orZ.janu
92EC                            .byte 73 7A 00 70 65 6C 63 00  ; sz.pelc.
92F4                            .byte 80 80 80 80 E1 F5 F4 EF  ; ........
92FC                            .byte F2 80 EB EF ED EE E1 F4  ; ........
9304                            .byte DA 80 80 80              ; ....
9308  20 13 98  ROOM_START      JSR LOAD_ROOM         ; load room ROOM, count hearts
930B  20 78 96  MAIN_LOOP       JSR SCAN              ; one physics tick (all objects incl. hero)
930E  AC FC 02                  LDY CH                ; key pressed?
9311  C0 FF                     CPY #$ff
9313  F0 09                     BEQ CHK_ROOM_DONE
9315  A9 FF                     LDA #$ff
9317  8D FC 02                  STA CH
931A  C0 1C                     CPY #$1c              ; ESC = suicide
931C  F0 0C                     BEQ HERO_DEAD
931E  2C C6 98  CHK_ROOM_DONE   BIT ROOM_DONE_FLAG    ; bit7 clear => room completed
9321  10 3A                     BPL ROOM_DONE
9323  A9 2A                     LDA #$2a              ; count hero cells ('*')
9325  20 AF 98                  JSR COUNT_CELLS
9328  D0 E1                     BNE MAIN_LOOP         ; hero alive => next tick
932A  A2 00     HERO_DEAD       LDX #$00              ; turn every hero into a blast (ESC)
932C  A9 2B                     LDA #$2b
932E  BC C0 9E  L932E           LDY GRID,X
9331  C0 2A                     CPY #$2a
9333  D0 03                     BNE L9338
9335  9D C0 9E                  STA GRID,X
9338  E8        L9338           INX
9339  E0 F0                     CPX #$f0
933B  90 F1                     BCC L932E
933D  A9 40                     LDA #$40              ; wait 64 frames while ticking (death animation)
933F  8D 1E 02                  STA CDTMV3
9342  20 78 96  DEATH_WAIT      JSR SCAN
9345  AD 1E 02                  LDA CDTMV3
9348  D0 F8                     BNE DEATH_WAIT
934A  CE C0 98                  DEC LIVES             ; lives-1; 0 is still playable, wrap to $FF = game over
934D  AD C0 98                  LDA LIVES
9350  C9 FF                     CMP #$ff
9352  D0 03                     BNE RELOAD_ROOM
9354  4C 60 92                  JMP PLAY              ; game over -> title
9357  20 96 93  RELOAD_ROOM     JSR SHOW_LIVES
935A  4C 08 93                  JMP ROOM_START
935D  EE C3 98  ROOM_DONE       INC ROOM              ; next room; wrap to room 0 after last (game never ends)
9360  AD C3 98                  LDA ROOM
9363  CD 02 70                  CMP P_ROOMS
9366  A9 00                     LDA #$00
9368  90 06                     BCC ROOM_BCD_INC
936A  8D C3 98                  STA ROOM
936D  8D C4 98                  STA ROOM_BCD
9370  F8        ROOM_BCD_INC    SED
9371  18                        CLC
9372  AD C4 98                  LDA ROOM_BCD
9375  69 01                     ADC #$01
9377  8D C4 98                  STA ROOM_BCD
937A  D8                        CLD
937B  CE C8 98                  DEC EXTRA_CTR         ; every P_EXTRA rooms: bonus life
937E  D0 88                     BNE ROOM_START
9380  EE C0 98                  INC LIVES
9383  D0 05                     BNE SHOW_LIVES2
9385  CE C0 98                  DEC LIVES
9388  D0 03                     BNE RESET_EXTRA
938A  20 96 93  SHOW_LIVES2     JSR SHOW_LIVES
938D  AD 01 70  RESET_EXTRA     LDA P_EXTRA
9390  8D C8 98                  STA EXTRA_CTR
9393  4C 08 93                  JMP ROOM_START
9396  A9 00     SHOW_LIVES      LDA #$00              ; LIVES -> BCD in LIVES_BCD (cap 99)
9398  8D C1 98                  STA LIVES_BCD
939B  AE C0 98                  LDX LIVES
939E  F0 12                     BEQ RTS1
93A0  F8        BCD_LOOP        SED
93A1  18                        CLC
93A2  AD C1 98                  LDA LIVES_BCD
93A5  69 01                     ADC #$01
93A7  90 02                     BCC L93AB
93A9  A9 99                     LDA #$99
93AB  8D C1 98  L93AB           STA LIVES_BCD
93AE  D8                        CLD
93AF  CA                        DEX
93B0  D0 EE                     BNE BCD_LOOP
93B2  60        RTS1            RTS
93B3  A9 2F     H_ROCK          LDA #$2f              ; rock at rest ($27 '\''): may wake into $2F
93B5  4C 6C 95                  JMP REST_CHECK
93B8  A9 28     H_ROCK_WAKE     LDA #$28              ; rock waking ($2F '/'): first move, becomes $28
93BA  A0 27                     LDY #$27
93BC  4C B1 95                  JMP MOVE_FALL
93BF  A9 02     H_ROCK_FALL     LDA #$02              ; rock falling ($28 '('): landing kills hero / detonates bombs
93C1  85 CB                     STA PTR
93C3  A9 28                     LDA #$28
93C5  A0 27                     LDY #$27
93C7  10 0D                     BPL FALL_STEP
93C9  A9 29     H_HEART         LDA #$29              ; heart at rest ($24 '$'): wakes DIRECTLY into $29 (no wake state)
93CB  4C 6C 95                  JMP REST_CHECK
93CE  A9 03     H_HEART_FALL    LDA #$03              ; heart falling ($29 ')')
93D0  85 CB                     STA PTR
93D2  A9 29                     LDA #$29
93D4  A0 24                     LDY #$24
93D6  85 CD     FALL_STEP       STA TMP               ; A=falling code, Y=rest code; probe cell below
93D8  84 CE                     STY TMP2
93DA  A0 03                     LDY #$03
93DC  20 F7 95                  JSR PROBE
93DF  90 16                     BCC FALL_MOVE         ; below empty -> keep falling
93E1  C9 2A                     CMP #$2a              ; below = hero -> hero cell becomes blast
93E3  F0 08                     BEQ HIT_DETONATE
93E5  C9 22                     CMP #$22              ; below = falling bomb
93E7  F0 04                     BEQ HIT_DETONATE
93E9  C9 26                     CMP #$26              ; below = bomb at rest
93EB  D0 0A                     BNE FALL_MOVE
93ED  A9 2B     HIT_DETONATE    LDA #$2b              ; write '+' (blast next tick) into cell below
93EF  99 C0 9E                  STA GRID,Y
93F2  A5 CB     LAND_SOUND      LDA PTR
93F4  4C 32 96                  JMP SND_REQ
93F7  A5 CD     FALL_MOVE       LDA TMP               ; move/roll/land via MOVE_FALL
93F9  A4 CE                     LDY TMP2
93FB  20 B1 95                  JSR MOVE_FALL
93FE  90 63                     BCC RTS2
9400  B0 F0                     BCS LAND_SOUND
9402  A9 2D     H_BOMB          LDA #$2d              ; bomb at rest ($26 '&'): may wake into $2D
9404  4C 6C 95                  JMP REST_CHECK
9407  A9 22     H_BOMB_WAKE     LDA #$22              ; bomb waking ($2D '-')
9409  A0 26                     LDY #$26
940B  4C B1 95                  JMP MOVE_FALL
940E  A0 03     H_BOMB_FALL     LDY #$03              ; bomb falling ($22 '"')
9410  20 F7 95                  JSR PROBE
9413  90 1F                     BCC BF_CONTINUE       ; below empty -> keep falling
9415  48                        PHA
9416  A9 02                     LDA #$02
9418  20 32 96                  JSR SND_REQ
941B  68                        PLA
941C  C9 2A                     CMP #$2a              ; below = hero -> hero explodes, bomb stays
941E  D0 06                     BNE BF_LANDED
9420  A9 2B                     LDA #$2b
9422  99 C0 9E                  STA GRID,Y
9425  60                        RTS
9426  C9 2E     BF_LANDED       CMP #$2e              ; below = grass -> lands softly, back to '&'
9428  D0 04                     BNE BF_EXPLODE
942A  A9 26                     LDA #$26
942C  D0 02                     BNE BF_STORE
942E  A9 2B     BF_EXPLODE      LDA #$2b              ; anything else below (rock, wall, border...) -> bomb becomes blast
9430  9D C0 9E  BF_STORE        STA GRID,X
9433  60                        RTS
9434  A9 22     BF_CONTINUE     LDA #$22
9436  A0 26                     LDY #$26
9438  4C B1 95                  JMP MOVE_FALL
943B  A0 03     H_BLAST         LDY #$03              ; blast ($2B '+'): 4 orthogonal neighbours only (dirs 3..0 = down,up,right,left)
943D  98        BL_LOOP         TYA
943E  48                        PHA
943F  20 F7 95                  JSR PROBE
9442  30 15                     BMI BL_NEXT           ; out of grid
9444  C9 25                     CMP #$25              ; hard wall '%' survives
9446  F0 11                     BEQ BL_NEXT
9448  C9 26                     CMP #$26              ; bomb -> chained blast next tick
944A  F0 04                     BEQ BL_CHAIN
944C  C9 2B                     CMP #$2b              ; '+' stays '+'
944E  D0 04                     BNE BL_DESTROY
9450  A9 AB     BL_CHAIN        LDA #$ab
9452  30 02                     BMI BL_STORE
9454  A9 B0     BL_DESTROY      LDA #$b0              ; everything else -> '0' (anim frame 0)
9456  99 C0 9E  BL_STORE        STA GRID,Y
9459  68        BL_NEXT         PLA
945A  A8                        TAY
945B  88                        DEY
945C  10 DF                     BPL BL_LOOP
945E  A9 B0                     LDA #$b0              ; centre -> '0'
9460  9D C0 9E                  STA GRID,X
9463  60        RTS2            RTS
9464  AD C2 98  H_EXIT          LDA HEARTS_LEFT       ; exit ('!'): blink tile when HEARTS_LEFT==0
9467  D0 FA                     BNE RTS2
9469  A5 D0                     LDA TICK
946B  29 04                     AND #$04
946D  08                        PHP
946E  AD CA 98                  LDA TILE_EXIT
9471  29 7F                     AND #$7f
9473  28                        PLP
9474  F0 02                     BEQ EX_STORE
9476  09 80                     ORA #$80
9478  8D CA 98  EX_STORE        STA TILE_EXIT
947B  60                        RTS
947C  AD 00 D3  H_HERO          LDA PORTA             ; hero: joystick 1&2 (active low) else keyboard
947F  C9 FF                     CMP #$ff
9481  F0 0B                     BEQ HERO_KBD
9483  4A                        LSR A                 ; merge both sticks
9484  4A                        LSR A
9485  4A                        LSR A
9486  4A                        LSR A
9487  2D 00 D3                  AND PORTA
948A  09 F0                     ORA #$f0
948C  30 0D                     BMI HERO_MATCH
948E  AD 0F D2  HERO_KBD        LDA SKSTAT            ; SKSTAT bit2: key down?
9491  29 04                     AND #$04
9493  D0 10                     BNE HERO_IDLE
9495  AC 09 D2                  LDY KBCODE            ; KBCODE -> ATASCII via OS table
9498  B9 51 FB                  LDA OS_KEYTAB,Y
949B  A0 0F     HERO_MATCH      LDY #$0f              ; match against KEYTAB (16 entries, index&3 = dir)
949D  D9 5C 95  HM_LOOP         CMP KEYTAB,Y
94A0  F0 0C                     BEQ HERO_MOVE
94A2  88                        DEY
94A3  10 F8                     BPL HM_LOOP
94A5  AD D3 98  HERO_IDLE       LDA TILE_HERO         ; no input: clear walk animation bits
94A8  29 FC                     AND #$fc
94AA  8D D3 98                  STA TILE_HERO
94AD  60                        RTS
94AE  98        HERO_MOVE       TYA                   ; dir: 0=left 1=right 2=up 3=down
94AF  29 03                     AND #$03
94B1  A8                        TAY
94B2  8C C5 98                  STY LAST_DIR
94B5  C0 02                     CPY #$02              ; push only for left/right
94B7  B0 17                     BCS HERO_TRY
94B9  AD D3 98                  LDA TILE_HERO         ; facing bits in TILE_HERO
94BC  29 F3                     AND #$f3
94BE  85 CD                     STA TMP
94C0  98                        TYA
94C1  48                        PHA
94C2  69 01                     ADC #$01
94C4  0A                        ASL A
94C5  0A                        ASL A
94C6  05 CD                     ORA TMP
94C8  8D D3 98                  STA TILE_HERO
94CB  20 E8 94                  JSR PUSH
94CE  68                        PLA
94CF  A8                        TAY
94D0  20 F7 95  HERO_TRY        JSR PROBE             ; target empty?
94D3  90 05                     BCC HERO_STEP
94D5  20 2E 95                  JSR ENTER_CELL        ; try heart/grass/exit
94D8  B0 0D                     BCS RTS3
94DA  BD C0 9E  HERO_STEP       LDA GRID,X            ; move hero (set bit7 = moved)
94DD  09 80                     ORA #$80
94DF  99 C0 9E                  STA GRID,Y
94E2  A9 20                     LDA #$20
94E4  9D C0 9E                  STA GRID,X
94E7  60        RTS3            RTS
94E8  8A        PUSH            TXA                   ; PUSH: cell beyond must be in grid
94E9  48                        PHA
94EA  18                        CLC
94EB  A5 00                     LDA CX
94ED  79 20 96                  ADC DX_TAB,Y
94F0  18                        CLC
94F1  79 20 96                  ADC DX_TAB,Y
94F4  C9 14                     CMP #$14              ; x+2*dx >= 20 -> fail
94F6  B0 33                     BCS PUSH_END
94F8  84 CD                     STY TMP
94FA  20 F7 95                  JSR PROBE
94FD  A2 28                     LDX #$28
94FF  C9 27                     CMP #$27              ; only rock at rest ('\'')
9501  F0 06                     BEQ PUSH_CHK
9503  A2 22                     LDX #$22
9505  C9 26                     CMP #$26              ; or bomb at rest ('&')
9507  D0 22                     BNE PUSH_END
9509  86 CE     PUSH_CHK        STX TMP2
950B  98                        TYA
950C  AA                        TAX
950D  A4 CD                     LDY TMP
950F  20 F7 95                  JSR PROBE             ; cell beyond object must be empty
9512  B0 17                     BCS PUSH_END
9514  A5 D0                     LDA TICK              ; push allowed on EVEN ticks only
9516  4A                        LSR A
9517  B0 12                     BCS PUSH_END
9519  A9 01                     LDA #$01
951B  20 32 96                  JSR SND_REQ
951E  BD C0 9E                  LDA GRID,X            ; move object (keeps rest code, bit7 set)
9521  09 80                     ORA #$80
9523  99 C0 9E                  STA GRID,Y
9526  A9 20                     LDA #$20
9528  9D C0 9E                  STA GRID,X
952B  68        PUSH_END        PLA
952C  AA                        TAX
952D  60                        RTS
952E  C9 24     ENTER_CELL      CMP #$24              ; '$' heart: HEARTS_LEFT-1, enter
9530  D0 0A                     BNE EC_GRASS
9532  CE C2 98                  DEC HEARTS_LEFT
9535  A9 03                     LDA #$03
9537  20 32 96                  JSR SND_REQ
953A  18                        CLC
953B  60                        RTS
953C  C9 2E     EC_GRASS        CMP #$2e              ; '.' grass: enter
953E  D0 07                     BNE EC_EXIT
9540  A9 01                     LDA #$01
9542  20 32 96                  JSR SND_REQ
9545  18                        CLC
9546  60                        RTS
9547  C9 21     EC_EXIT         CMP #$21              ; '!' exit: only when HEARTS_LEFT==0
9549  D0 0F                     BNE EC_BLOCKED
954B  AD C2 98                  LDA HEARTS_LEFT
954E  D0 0A                     BNE EC_BLOCKED
9550  8D C6 98                  STA ROOM_DONE_FLAG    ; ROOM_DONE_FLAG=0 (bit7 clear = done)
9553  A9 21                     LDA #$21
9555  9D C0 9E                  STA GRID,X
9558  18                        CLC
9559  60                        RTS
955A  38        EC_BLOCKED      SEC                   ; blocked
955B  60                        RTS
955C            KEYTAB          .byte FB F7 FE FD 6F 70 71 61  ; ....opqa  ; joystick nibbles L,R,U,D; then keys o p q a; + * - =; 6 9 8 7
9564                            .byte 2B 2A 2D 3D 36 39 38 37  ; +*-=6987
956C  85 CD     REST_CHECK      STA TMP               ; REST_CHECK: A=wake code. Object at rest decides whether to wake
956E  A0 03                     LDY #$03
9570  20 F7 95                  JSR PROBE
9573  49 2E                     EOR #$2e              ; below '.': stay
9575  F0 33                     BEQ RTS4
9577  49 2E                     EOR #$2e
9579  49 25                     EOR #$25              ; below '%': stay
957B  F0 2D                     BEQ RTS4
957D  49 25                     EOR #$25
957F  49 2A                     EOR #$2a              ; below '*' hero: stay
9581  F0 27                     BEQ RTS4
9583  90 26                     BCC RC_WAKE           ; below empty -> wake (no move this tick)
9585  A0 02                     LDY #$02              ; cell above holds same wake code -> stay
9587  20 F7 95                  JSR PROBE
958A  C5 CD                     CMP TMP
958C  F0 1C                     BEQ RTS4
958E  A0 00                     LDY #$00              ; left empty AND down-left empty -> wake (roll)
9590  20 F7 95                  JSR PROBE
9593  D0 07                     BNE RC_RIGHT
9595  A0 04                     LDY #$04
9597  20 F7 95                  JSR PROBE
959A  90 0F                     BCC RC_WAKE
959C  A0 01     RC_RIGHT        LDY #$01              ; right empty AND down-right empty -> wake (roll)
959E  20 F7 95                  JSR PROBE
95A1  D0 07                     BNE RTS4
95A3  A0 05                     LDY #$05
95A5  20 F7 95                  JSR PROBE
95A8  90 01                     BCC RC_WAKE
95AA  60        RTS4            RTS
95AB  A5 CD     RC_WAKE         LDA TMP               ; store wake code in place (no bit7)
95AD  9D C0 9E                  STA GRID,X
95B0  60                        RTS
95B1  09 80     MOVE_FALL       ORA #$80              ; MOVE_FALL: A=falling code, Y=rest code. Clears own cell first
95B3  85 CD                     STA TMP
95B5  84 CE                     STY TMP2
95B7  A9 20                     LDA #$20
95B9  9D C0 9E                  STA GRID,X
95BC  A0 03                     LDY #$03              ; below empty -> move down
95BE  20 F7 95                  JSR PROBE
95C1  B0 09                     BCS MF_BLOCKED
95C3  90 01                     BCC MF_PUT
95C5  38        MF_ROLL         SEC
95C6  A5 CD     MF_PUT          LDA TMP
95C8  99 C0 9E                  STA GRID,Y
95CB  60                        RTS
95CC  C9 2E     MF_BLOCKED      CMP #$2e              ; below '.' or '%' -> rest
95CE  F0 20                     BEQ MF_REST
95D0  C9 25                     CMP #$25
95D2  F0 1C                     BEQ MF_REST
95D4  A0 04                     LDY #$04              ; down-left AND left empty -> move DIAGONALLY down-left (one tick)
95D6  20 F7 95                  JSR PROBE
95D9  B0 07                     BCS MF_RIGHT
95DB  A0 00                     LDY #$00
95DD  20 F7 95                  JSR PROBE
95E0  90 E3                     BCC MF_ROLL
95E2  A0 05     MF_RIGHT        LDY #$05              ; else down-right AND right empty -> diagonal down-right
95E4  20 F7 95                  JSR PROBE
95E7  B0 07                     BCS MF_REST
95E9  A0 01                     LDY #$01
95EB  20 F7 95                  JSR PROBE
95EE  90 D5                     BCC MF_ROLL
95F0  A5 CE     MF_REST         LDA TMP2              ; else rest in place, C=1
95F2  9D C0 9E                  STA GRID,X
95F5  38                        SEC
95F6  60                        RTS
95F7  18        PROBE           CLC                   ; PROBE: Y=dir (0..5). Out of grid -> A=$FF,C=1 (solid border). Else A=cell&$7F, Y=index, C=occupied
95F8  A5 00                     LDA CX
95FA  79 20 96                  ADC DX_TAB,Y
95FD  C9 14                     CMP #$14
95FF  90 03                     BCC PR_Y
9601  A9 FF     PR_OUT          LDA #$ff
9603  60                        RTS
9604  18        PR_Y            CLC
9605  A5 01                     LDA CY
9607  79 26 96                  ADC DY_TAB,Y
960A  C9 0C                     CMP #$0c
960C  B0 F3                     BCS PR_OUT
960E  18                        CLC
960F  8A                        TXA
9610  79 2C 96                  ADC DIDX_TAB,Y
9613  A8                        TAY
9614  B9 C0 9E                  LDA GRID,Y
9617  29 7F                     AND #$7f
9619  C9 20                     CMP #$20
961B  18                        CLC
961C  F0 01                     BEQ RTS5
961E  38                        SEC
961F  60        RTS5            RTS
9620            DX_TAB          .byte FF 01 00 00 FF 01        ; ......  ; dx: L R U D DL DR
9626            DY_TAB          .byte 00 00 FF 01 01 01        ; ......  ; dy
962C            DIDX_TAB        .byte FF 01 EC 14 13 15        ; ......  ; index delta: -1 +1 -20 +20 +19 +21
9632  CD C7 98  SND_REQ         CMP SND_PRI
9635  90 03                     BCC RTS6
9637  8D C7 98                  STA SND_PRI
963A  60        RTS6            RTS
963B  AC C7 98  SND_PLAY        LDY SND_PRI
963E  F0 2F                     BEQ RTS7
9640  88                        DEY
9641  20 0C 98                  JSR WAIT_VBL
9644  AD 1A D2                  LDA RANDOM
9647  29 0F                     AND #$0f
9649  69 08                     ADC #$08
964B  8D 72 96                  STA SND_F2
964E  B9 74 96                  LDA SND_C,Y
9651  C0 03                     CPY #$03
9653  90 06                     BCC L965B
9655  98                        TYA
9656  A0 03                     LDY #$03
9658  19 74 96                  ORA SND_C,Y
965B  8D 01 D2  L965B           STA AUDC1
965E  B9 70 96                  LDA SND_F,Y
9661  8D 00 D2                  STA AUDF1
9664  20 0C 98                  JSR WAIT_VBL
9667  A9 00                     LDA #$00
9669  8D 01 D2                  STA AUDC1
966C  8D C7 98                  STA SND_PRI
966F  60        RTS7            RTS
9670            SND_F           .byte 00 04                    ; ..
9672            SND_F2          .byte 00 10                    ; ..
9674            SND_C           .byte 81 04 A4 00              ; ....
9678  A2 FF     SCAN            LDX #$ff              ; SCAN: X=0..239 TOP-DOWN, LEFT-TO-RIGHT. bit7 = moved this tick -> skip
967A  8E C5 98                  STX LAST_DIR
967D  8E C6 98                  STX ROOM_DONE_FLAG
9680  E8                        INX
9681  86 00                     STX CX
9683  86 01                     STX CY
9685  BD C0 9E  SC_CELL         LDA GRID,X
9688  30 35                     BMI SC_NEXT
968A  C9 30                     CMP #$30              ; values >= $30 are blast anim frames '0'..'6': advance, '7' -> space
968C  90 18                     BCC SC_DISPATCH
968E  48                        PHA
968F  38                        SEC
9690  E9 30                     SBC #$30
9692  69 03                     ADC #$03
9694  20 32 96                  JSR SND_REQ
9697  18                        CLC
9698  68                        PLA
9699  69 01                     ADC #$01
969B  C9 37                     CMP #$37
969D  90 02                     BCC SC_ANIM_PUT
969F  A9 20                     LDA #$20
96A1  9D C0 9E  SC_ANIM_PUT     STA GRID,X
96A4  D0 19                     BNE SC_NEXT
96A6  29 0F     SC_DISPATCH     AND #$0f              ; low nibble -> HANDLER_TAB (self-modifying JSR)
96A8  0A                        ASL A
96A9  A8                        TAY
96AA  B9 E1 98                  LDA HANDLER_TAB_HI,Y
96AD  F0 10                     BEQ SC_NEXT
96AF  8D BC 96                  STA D96BC
96B2  B9 E0 98                  LDA HANDLER_TAB,Y
96B5  8D BB 96                  STA D96BB
96B8  8A                        TXA
96B9  48                        PHA
96BA  20 BA 96  DISPATCH_JSR    JSR DISPATCH_JSR
96BD  68                        PLA
96BE  AA                        TAX
96BF  E6 00     SC_NEXT         INC CX
96C1  A5 00                     LDA CX
96C3  C9 14                     CMP #$14
96C5  90 06                     BCC SC_INX
96C7  A9 00                     LDA #$00
96C9  85 00                     STA CX
96CB  E6 01                     INC CY
96CD  E8        SC_INX          INX
96CE  E0 F0                     CPX #$f0
96D0  90 B3                     BCC SC_CELL
96D2  A2 EF                     LDX #$ef              ; clear moved bits
96D4  BD C0 9E  CLR_MOVED       LDA GRID,X
96D7  29 7F                     AND #$7f
96D9  9D C0 9E                  STA GRID,X
96DC  CA                        DEX
96DD  E0 FF                     CPX #$ff
96DF  D0 F3                     BNE CLR_MOVED
96E1  AD D3 98                  LDA TILE_HERO
96E4  AC C5 98                  LDY LAST_DIR
96E7  30 07                     BMI HERO_ANIM0
96E9  AD D3 98                  LDA TILE_HERO
96EC  49 02                     EOR #$02
96EE  D0 02                     BNE HERO_ANIM_PUT
96F0  29 FE     HERO_ANIM0      AND #$fe
96F2  8D D3 98  HERO_ANIM_PUT   STA TILE_HERO
96F5  A5 D0                     LDA TICK              ; heart tiles blink every tick
96F7  29 01                     AND #$01
96F9  D0 10                     BNE TICK_END
96FB  AD CD 98                  LDA TILE_HEART
96FE  49 80                     EOR #$80
9700  8D CD 98                  STA TILE_HEART
9703  AD D2 98                  LDA TILE_HEART_F
9706  49 80                     EOR #$80
9708  8D D2 98                  STA TILE_HEART_F
970B  20 3B 96  TICK_END        JSR SND_PLAY
970E  46 4D                     LSR ATRACT
9710  A5 11                     LDA BRKKEY
9712  30 03                     BMI WAIT_TICK
9714  4C 60 92                  JMP PLAY
9717  AD 1C 02  WAIT_TICK       LDA CDTMV2            ; wait CDTMV2 == 0
971A  D0 FB                     BNE WAIT_TICK
971C  A9 06                     LDA #$06              ; 6 frames per tick
971E  8D 1C 02                  STA CDTMV2
9721  E6 D0                     INC TICK
9723  A2 00     RENDER          LDX #$00              ; RENDER: each cell = 2x2 chars from TILE_TAB[cell]
9725  A9 00                     LDA #$00
9727  85 CB                     STA PTR
9729  A9 9B                     LDA #$9b
972B  85 CC                     STA PTR+1
972D  A9 13     RN_ROW          LDA #$13
972F  85 CD                     STA TMP
9731  BC C0 9E  RN_CELL         LDY GRID,X
9734  B9 A9 98                  LDA D98A9,Y
9737  A0 00                     LDY #$00
9739  91 CB                     STA (PTR),Y
973B  09 01                     ORA #$01
973D  C8                        INY
973E  91 CB                     STA (PTR),Y
9740  09 20                     ORA #$20
9742  A0 29                     LDY #$29
9744  91 CB                     STA (PTR),Y
9746  29 FE                     AND #$fe
9748  88                        DEY
9749  91 CB                     STA (PTR),Y
974B  18                        CLC
974C  A5 CB                     LDA PTR
974E  69 02                     ADC #$02
9750  85 CB                     STA PTR
9752  90 02                     BCC RN_NEXT
9754  E6 CC                     INC PTR+1
9756  E8        RN_NEXT         INX
9757  C6 CD                     DEC TMP
9759  10 D6                     BPL RN_CELL
975B  18                        CLC
975C  A5 CB                     LDA PTR
975E  69 28                     ADC #$28
9760  85 CB                     STA PTR
9762  90 02                     BCC RN_ROW_END
9764  E6 CC                     INC PTR+1
9766  E0 F0     RN_ROW_END      CPX #$f0
9768  90 C3                     BCC RN_ROW
976A  AD C1 98                  LDA LIVES_BCD         ; status: lives at +9, room at +$23
976D  A0 09                     LDY #$09
976F  20 77 97                  JSR PUT_BCD
9772  AD C4 98                  LDA ROOM_BCD
9775  A0 23                     LDY #$23
9777  48        PUT_BCD         PHA
9778  20 80 97                  JSR PUT_DIGIT
977B  68                        PLA
977C  4A                        LSR A
977D  4A                        LSR A
977E  4A                        LSR A
977F  4A                        LSR A
9780  29 0F     PUT_DIGIT       AND #$0f
9782  18                        CLC
9783  69 40                     ADC #$40
9785  99 A4 92                  STA STATUS_LINE,Y
9788  88                        DEY
9789  60                        RTS
978A  A9 E0     TITLE_INIT      LDA #$e0              ; title screen
978C  85 11                     STA BRKKEY
978E  A2 8B                     LDX #$8b
9790  A0 92                     LDY #$92
9792  20 D5 97                  JSR SET_DISPLAY
9795  46 4D     WAIT_START      LSR ATRACT            ; wait: START (CONSOL) or SHIFT (SKSTAT bit3) or TRIG0/1
9797  AD 0F D2                  LDA SKSTAT
979A  4A                        LSR A
979B  4A                        LSR A
979C  4A                        LSR A
979D  2D 1F D0                  AND CONSOL
97A0  2D 10 D0                  AND TRIG0
97A3  2D 11 D0                  AND TRIG1
97A6  D0 ED                     BNE WAIT_START
97A8  A2 00                     LDX #$00
97AA  8E C3 98                  STX ROOM
97AD  E8                        INX
97AE  8E C4 98                  STX ROOM_BCD
97B1  A0 EF                     LDY #$ef
97B3  A9 20                     LDA #$20
97B5  99 C0 9E  CLR_GRID        STA GRID,Y
97B8  88                        DEY
97B9  C0 FF                     CPY #$ff
97BB  D0 F8                     BNE CLR_GRID
97BD  AD 00 70                  LDA P_LIVES           ; LIVES from P_LIVES
97C0  8D C0 98                  STA LIVES
97C3  20 96 93                  JSR SHOW_LIVES
97C6  AD 01 70                  LDA P_EXTRA           ; EXTRA_CTR from P_EXTRA
97C9  8D C8 98                  STA EXTRA_CTR
97CC  20 23 97                  JSR RENDER
97CF  A9 90                     LDA #$90              ; game display list, CHBAS=$90
97D1  A2 69                     LDX #$69
97D3  A0 92                     LDY #$92
97D5  8D F4 02  SET_DISPLAY     STA CHBAS
97D8  A9 00                     LDA #$00
97DA  8D 00 D4                  STA DMACTL
97DD  8D 2F 02                  STA SDMCTL
97E0  8E 30 02                  STX SDLSTL
97E3  8C 31 02                  STY SDLSTH
97E6  A2 13                     LDX #$13
97E8  A9 00     TITLE_CONV      LDA #$00              ; zero CHARSET[0..19]; title ATASCII->screen code into TITLE_LINE
97EA  9D 00 90                  STA CHARSET,X
97ED  BD 03 70                  LDA P_TITLE,X
97F0  0A                        ASL A
97F1  08                        PHP
97F2  C9 C0                     CMP #$c0
97F4  B0 06                     BCS TC_PUT
97F6  E9 3E                     SBC #$3e
97F8  B0 02                     BCS TC_PUT
97FA  69 C0                     ADC #$c0
97FC  28        TC_PUT          PLP
97FD  6A                        ROR A
97FE  9D C0 9F                  STA TITLE_LINE,X
9801  CA                        DEX
9802  10 E4                     BPL TITLE_CONV
9804  20 0C 98                  JSR WAIT_VBL
9807  A9 22                     LDA #$22
9809  8D 2F 02                  STA SDMCTL
980C  A5 14     WAIT_VBL        LDA RTCLOK
980E  C5 14     WV_LOOP         CMP RTCLOK
9810  F0 FC                     BEQ WV_LOOP
9812  60                        RTS
9813  A9 17     LOAD_ROOM       LDA #$17              ; src = P_TITLE+20 + ROOM*240
9815  85 CD                     STA TMP
9817  A9 70                     LDA #$70
9819  85 CE                     STA TMP2
981B  AE C3 98                  LDX ROOM
981E  F0 0E                     BEQ LR_CURTAIN
9820  38        LR_ADD240       SEC
9821  A9 EF                     LDA #$ef
9823  65 CD                     ADC TMP
9825  85 CD                     STA TMP
9827  90 02                     BCC LR_DEX
9829  E6 CE                     INC TMP2
982B  CA        LR_DEX          DEX
982C  D0 F2                     BNE LR_ADD240
982E  A9 80     LR_CURTAIN      LDA #$80              ; curtain of '#' then reveal
9830  20 54 98                  JSR CURTAIN
9833  AD D3 98                  LDA TILE_HERO
9836  29 FC                     AND #$fc
9838  8D D3 98                  STA TILE_HERO
983B  AD CA 98                  LDA TILE_EXIT
983E  29 7F                     AND #$7f
9840  8D CA 98                  STA TILE_EXIT
9843  20 54 98                  JSR CURTAIN
9846  A9 24                     LDA #$24              ; HEARTS_LEFT = count('$')
9848  20 AF 98                  JSR COUNT_CELLS
984B  8D C2 98                  STA HEARTS_LEFT
984E  A9 FF                     LDA #$ff
9850  8D FC 02                  STA CH
9853  60                        RTS
9854  8D AE 98  CURTAIN         STA CURTAIN_MODE
9857  A2 19                     LDX #$19
9859  8A        CU_ROUND        TXA
985A  48                        PHA
985B  A2 28                     LDX #$28
985D  AC 1A D2  CU_RND          LDY RANDOM
9860  C0 F0                     CPY #$f0
9862  B0 F9                     BCS CU_RND
9864  20 97 98                  JSR PUT_CELL
9867  CA                        DEX
9868  D0 F3                     BNE CU_RND
986A  20 7C 98                  JSR CURTAIN_FRAME
986D  68                        PLA
986E  AA                        TAX
986F  CA                        DEX
9870  D0 E7                     BNE CU_ROUND
9872  A0 00                     LDY #$00
9874  20 97 98  CU_FILL         JSR PUT_CELL
9877  C8                        INY
9878  C0 F0                     CPY #$f0
987A  90 F8                     BCC CU_FILL
987C  A5 CD     CURTAIN_FRAME   LDA TMP
987E  48                        PHA
987F  A5 CE                     LDA TMP2
9881  48                        PHA
9882  20 0C 98                  JSR WAIT_VBL
9885  20 23 97                  JSR RENDER
9888  A9 03                     LDA #$03
988A  20 32 96                  JSR SND_REQ
988D  20 3B 96                  JSR SND_PLAY
9890  68                        PLA
9891  85 CE                     STA TMP2
9893  68                        PLA
9894  85 CD                     STA TMP
9896  60                        RTS
9897  B1 CD     PUT_CELL        LDA (TMP),Y           ; PUT_CELL: chars outside $20..$2F become rock ('@' -> $27)
9899  2C AE 98                  BIT CURTAIN_MODE
989C  10 02                     BPL PC_RANGE
989E  A9 23                     LDA #$23
98A0  C9 20     PC_RANGE        CMP #$20
98A2  90 04                     BCC PC_ROCK
98A4  C9 30                     CMP #$30
98A6  90 02                     BCC PC_STORE
98A8  A9 27     PC_ROCK         LDA #$27
98AA  99 C0 9E  PC_STORE        STA GRID,Y
98AD  60                        RTS
98AE            CURTAIN_MODE    .byte 00                       ; .
98AF  A2 00     COUNT_CELLS     LDX #$00              ; COUNT_CELLS: X = number of cells == A
98B1  A0 00                     LDY #$00
98B3  D9 C0 9E  CC_LOOP         CMP GRID,Y
98B6  D0 01                     BNE CC_NEXT
98B8  E8                        INX
98B9  C8        CC_NEXT         INY
98BA  C0 F0                     CPY #$f0
98BC  90 F5                     BCC CC_LOOP
98BE  8A                        TXA
98BF  60                        RTS
98C0            LIVES           .byte 00                       ; .
98C1            LIVES_BCD       .byte 00                       ; .
98C2            HEARTS_LEFT     .byte 00                       ; .
98C3            ROOM            .byte 00                       ; .
98C4            ROOM_BCD        .byte 00                       ; .
98C5            LAST_DIR        .byte 00                       ; .
98C6            ROOM_DONE_FLAG  .byte 00                       ; .
98C7            SND_PRI         .byte 00                       ; .
98C8            EXTRA_CTR       .byte 00                       ; .
98C9            TILE_TAB        .byte 00                       ; .  ; TILE_TAB[$20..$36]: tile base char per cell code (bit7 = colour)
98CA            TILE_EXIT       .byte 9C 12 0A                 ; ...
98CD            TILE_HEART      .byte 90 9E 12 0C 0C           ; .....
98D2            TILE_HEART_F    .byte 90                       ; .
98D3            TILE_HERO       .byte 18 02 08 12 0E 0C 02 04  ; ........
98DB                            .byte 06 08 06 04 02           ; .....
98E0            HANDLER_TAB     .byte 00                       ; .  ; HANDLER_TAB: 16 words indexed by cell low nibble
98E1            HANDLER_TAB_HI  .byte 00 64 94 0E 94 00 00 C9  ; .d......
98E9                            .byte 93 00 00 02 94 B3 93 BF  ; ........
98F1                            .byte 93 CE 93 7C 94 3B 94 00  ; ...|.;..
98F9                            .byte 00 07 94 00 00 B8 93 00  ; ........
9901                            .byte 00 00 00 00 00 00 00     ; .......
