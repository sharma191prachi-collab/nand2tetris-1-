#!/usr/bin/env python3
"""
Tiny Hack CPU simulator to double-check Box.hack without the CPU Emulator.
Usage: python verify_box.py Box.hack [K]
"""
import sys

SCREEN, KBD = 16384, 24576

def run(program, cycles, ram, key):
    a = d = pc = 0
    ram[KBD] = key
    for _ in range(cycles):
        ins = program[pc]
        if ins[0] == "0":                      # A-instruction
            a, pc = int(ins, 2), pc + 1
            continue
        use_m = ins[3] == "1"
        y = ram.get(a, 0) if use_m else a
        c = ins[4:10]
        x = d
        sx = lambda v: v - 65536 if v & 0x8000 else v
        table = {"101010": 0, "111111": 1, "111010": -1, "001100": x, "110000": y,
                 "001101": ~x, "110001": ~y, "001111": -x, "110011": -y,
                 "011111": x + 1, "110111": y + 1, "001110": x - 1, "110010": y - 1,
                 "000010": x + y, "010011": x - y, "000111": y - x,
                 "000000": x & y, "010101": x | y}
        out = sx(table[c] & 0xFFFF)
        dest, jump = ins[10:13], ins[13:16]
        old_a = a
        if dest[2] == "1": ram[old_a] = out & 0xFFFF
        if dest[1] == "1": d = out & 0xFFFF
        if dest[0] == "1": a = out & 0xFFFF
        jmp = (jump[0] == "1" and out < 0) or (jump[1] == "1" and out == 0) or (jump[2] == "1" and out > 0)
        pc = old_a if jmp else pc + 1
    return ram

def main():
    prog = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    K = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    words = ((K % 4) + 1)            # 16 px per word
    first_row, rows = K, 20
    ram = {}
    ok = True
    for label, key in (("key pressed", 65), ("key released", 0), ("pressed again", 65)):
        run(prog, 4000, ram, key)
        for row in range(0, 256):
            for w in range(32):
                value = ram.get(SCREEN + 32 * row + w, 0)
                inside = first_row <= row < first_row + rows and w < words
                want = 0xFFFF if (inside and key) else 0
                if value != want:
                    ok = False
                    print(f"[{label}] MISMATCH row {row} word {w}: got {value}, want {want}")
        print(f"[{label}] checked all 8192 screen words")
    print("RESULT:", "PASS - box is correct for K =", K if ok else "FAIL")
    return 0 if ok else 1

sys.exit(main())
