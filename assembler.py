#!/usr/bin/env python3
"""
Hack Assembler (Nand to Tetris, Capstone Part B)
Usage:  python assembler.py Prog.asm        ->  writes Prog.hack
K = 53  ->  K mod 3 = 2.
Extra feature (K mod 3 == 2): after a successful assembly the assembler prints
a SYMBOL TABLE (labels and variables with their addresses) and writes a
listing file Prog.lst (ROM address | binary | source line).
Wrong lines also print "Line N: ..." instead of crashing; all errors are
reported and no .hack file is written if any error is found.
"""
import re
import sys

# ---------- tables ----------
COMP = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "!D": "0001101", "!A": "0110001",
    "-D": "0001111", "-A": "0110011", "D+1": "0011111", "A+1": "0110111",
    "D-1": "0001110", "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    "M": "1110000", "!M": "1110001", "-M": "1110011", "M+1": "1110111",
    "M-1": "1110010", "D+M": "1000010", "D-M": "1010011", "M-D": "1000111",
    "D&M": "1000000", "D|M": "1010101",
}
JUMP = {"": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
        "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111"}
PREDEFINED = {"SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
              "SCREEN": 16384, "KBD": 24576}
PREDEFINED.update({f"R{i}": i for i in range(16)})
SYMBOL_RE = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


class AsmError(Exception):
    """A problem with one source line."""


def clean(line):
    """Remove comments and every whitespace character."""
    return re.sub(r"\s+", "", line.split("//", 1)[0])


def comp_bits(text):
    if text in COMP:
        return COMP[text]
    # accept the commutative spellings: A+D, M+D, A&D, M|D ...
    for op in "+&|":
        if op in text:
            left, _, right = text.partition(op)
            swapped = right + op + left
            if swapped in COMP:
                return COMP[swapped]
    raise AsmError(f"unknown computation '{text}'")


def dest_bits(text):
    if text == "":
        return "000"
    if any(c not in "ADM" for c in text) or len(set(text)) != len(text):
        raise AsmError(f"unknown destination '{text}'")
    return ("1" if "A" in text else "0") + ("1" if "D" in text else "0") + ("1" if "M" in text else "0")


def jump_bits(text):
    if text not in JUMP:
        raise AsmError(f"unknown jump '{text}'")
    return JUMP[text]


def encode_c(code):
    dest, comp, jump = "", code, ""
    if "=" in code:
        dest, _, comp = code.partition("=")
    if ";" in comp:
        comp, _, jump = comp.partition(";")
    if comp == "":
        raise AsmError("missing computation")
    return "111" + comp_bits(comp) + dest_bits(dest) + jump_bits(jump)


def encode_a(code, symbols, state):
    body = code[1:]
    if body == "":
        raise AsmError("'@' has no address or symbol")
    if body.isdigit():
        value = int(body)
        if value > 32767:
            raise AsmError(f"address {value} is too big (max 32767)")
    elif SYMBOL_RE.match(body):
        if body not in symbols:               # new variable
            symbols[body] = state["next_var"]
            state["next_var"] += 1
        value = symbols[body]
    else:
        raise AsmError(f"'{body}' is not a valid number or symbol")
    return format(value, "016b")


def assemble(lines):
    """Returns (hack_lines, errors, labels, variables, listing)."""
    errors, symbols = [], dict(PREDEFINED)
    labels = {}                # label name -> ROM address

    # ---------- first reading: find labels ----------
    instructions = []          # (line_number, text)
    for number, raw in enumerate(lines, start=1):
        text = clean(raw)
        if not text:
            continue
        if text.startswith("("):
            if not text.endswith(")") or not SYMBOL_RE.match(text[1:-1]):
                errors.append(f"Line {number}: invalid label '{text}'")
                continue
            name = text[1:-1]
            if name in symbols:
                errors.append(f"Line {number}: label '{name}' is already defined")
                continue
            symbols[name] = len(instructions)
            labels[name] = len(instructions)
        else:
            instructions.append((number, text))

    # ---------- second reading: translate ----------
    state, output, listing = {"next_var": 16}, [], []
    for number, text in instructions:
        try:
            code = encode_a(text, symbols, state) if text[0] == "@" else encode_c(text)
            output.append(code)
            listing.append((len(output) - 1, code, text))
        except AsmError as why:
            errors.append(f"Line {number}: invalid instruction '{text}' - {why}")
    errors.sort(key=lambda e: int(e.split()[1].rstrip(":")))   # show in line order
    variables = {n: a for n, a in symbols.items() if n not in PREDEFINED and n not in labels}
    return output, errors, labels, variables, listing


def main():
    if len(sys.argv) != 2 or not sys.argv[1].lower().endswith(".asm"):
        print("Usage: python assembler.py <file.asm>")
        return 2
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as why:
        print(f"Cannot read '{path}': {why.strerror}")
        return 2

    hack, errors, labels, variables, listing = assemble(lines)
    if errors:
        for message in errors:
            print(message)
        print(f"Assembly failed: {len(errors)} error(s). No .hack file written.")
        return 1

    out_path = path[:-4] + ".hack"
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(hack) + "\n")
    print(f"OK: {len(hack)} instructions written to {out_path}")

    # ---------- extra feature (K mod 3 == 2): symbol table + listing ----------
    print("\nSYMBOL TABLE")
    print(f"{'Symbol':<16}{'Address':>8}  Type")
    for name, addr in sorted(labels.items(), key=lambda x: x[1]):
        print(f"{name:<16}{addr:>8}  label (ROM)")
    for name, addr in sorted(variables.items(), key=lambda x: x[1]):
        print(f"{name:<16}{addr:>8}  variable (RAM)")

    lst_path = path[:-4] + ".lst"
    with open(lst_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("ROM  BINARY            SOURCE\n")
        for addr, code, text in listing:
            f.write(f"{addr:<5}{code}  {text}\n")
    print(f"\nListing written to {lst_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())