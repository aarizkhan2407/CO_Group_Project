import sys

# ─────────────────────────────────────────────
#  CLI argument handling
# ─────────────────────────────────────────────
if len(sys.argv) < 3:
    print("Usage: Simulator.py <input.bin> <output_trace.txt>")
    sys.exit(1)

input_file  = sys.argv[1]
output_file = sys.argv[2]

# ─────────────────────────────────────────────
#  Memory layout (from spec)
#  Program mem : 0x00000000 – 0x000000FF  (256 B, 64 × 32-bit words)
#  Stack mem   : 0x00000100 – 0x0000017F  (128 B, 32 × 32-bit words)
#  Data mem    : 0x00010000 – 0x0001007F  (128 B, 32 × 32-bit words)
#  SP init     : 0x0000017C
# ─────────────────────────────────────────────
PROG_MEM_BASE  = 0x00000000
PROG_MEM_END   = 0x000000FF
STACK_MEM_BASE = 0x00000100
STACK_MEM_END  = 0x0000017F
DATA_MEM_BASE  = 0x00010000
DATA_MEM_END   = 0x0001007F

# Unified memory: keyed by byte address, stores 32-bit int
memory = {}

# ─────────────────────────────────────────────
#  Registers  x0–x31  (32-bit signed ints stored as Python ints)
#  x0 is always 0; x2 (sp) initialised to 0x0000017C
# ─────────────────────────────────────────────
registers = [0] * 32
registers[2] = 0x0000017C   # sp

# ─────────────────────────────────────────────
#  Helper: sign-extend a value that is `bits` wide
# ─────────────────────────────────────────────
def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)

# ─────────────────────────────────────────────
#  Helper: force a Python int into 32-bit signed range
# ─────────────────────────────────────────────
def to32(value):
    value = value & 0xFFFFFFFF
    if value >= 0x80000000:
        value -= 0x100000000
    return value

# ─────────────────────────────────────────────
#  Helper: force a Python int into 32-bit unsigned range
# ─────────────────────────────────────────────
def to32u(value):
    return value & 0xFFFFFFFF

# ─────────────────────────────────────────────
#  Memory read/write (word-addressed, little-endian byte storage)
# ─────────────────────────────────────────────
def mem_write(addr, value):
    addr = addr & 0xFFFFFFFF
    value = to32u(value)
    memory[addr] = value

def mem_read(addr):
    addr = addr & 0xFFFFFFFF
    return memory.get(addr, 0)

# ─────────────────────────────────────────────
#  Register write (enforces x0 = 0)
# ─────────────────────────────────────────────
def reg_write(rd, value):
    if rd != 0:
        registers[rd] = to32(value)

# ─────────────────────────────────────────────
#  Load binary program into program memory
# ─────────────────────────────────────────────
with open(input_file, "r") as fin:
    prog_lines = [l.strip() for l in fin.readlines() if l.strip()]

if len(prog_lines) > 64:
    print("Error: program exceeds program memory size (64 instructions max)")
    sys.exit(1)

instructions = []
for idx, bits in enumerate(prog_lines):
    if len(bits) != 32 or not all(c in '01' for c in bits):
        print(f"Error at line {idx+1}: invalid binary word '{bits}'")
        sys.exit(1)
    addr = PROG_MEM_BASE + idx * 4
    mem_write(addr, int(bits, 2))
    instructions.append(bits)

# ─────────────────────────────────────────────
#  Decode helpers
# ─────────────────────────────────────────────
def bits(word, hi, lo):
    """Extract bits [hi:lo] (inclusive) from a 32-bit integer."""
    mask = (1 << (hi - lo + 1)) - 1
    return (word >> lo) & mask

def decode_and_execute(pc):
    """
    Decode the 32-bit instruction at `pc`, execute it, return new PC.
    Returns None to signal HALT.
    """
    word = mem_read(pc)
    opcode = bits(word, 6, 0)

    # ── R-type  opcode = 0110011 ─────────────────────────────────────
    if opcode == 0b0110011:
        rd     = bits(word, 11,  7)
        funct3 = bits(word, 14, 12)
        rs1    = bits(word, 19, 15)
        rs2    = bits(word, 24, 20)
        funct7 = bits(word, 31, 25)

        a = registers[rs1]
        b = registers[rs2]

        if   funct3 == 0b000 and funct7 == 0b0000000:  # add
            reg_write(rd, a + b)
        elif funct3 == 0b000 and funct7 == 0b0100000:  # sub
            reg_write(rd, a - b)
        elif funct3 == 0b001:                           # sll
            reg_write(rd, a << (to32u(b) & 0x1F))
        elif funct3 == 0b010:                           # slt
            reg_write(rd, 1 if a < b else 0)
        elif funct3 == 0b011:                           # sltu
            reg_write(rd, 1 if to32u(a) < to32u(b) else 0)
        elif funct3 == 0b100:                           # xor
            reg_write(rd, a ^ b)
        elif funct3 == 0b101 and funct7 == 0b0000000:  # srl
            reg_write(rd, to32u(a) >> (to32u(b) & 0x1F))
        elif funct3 == 0b110:                           # or
            reg_write(rd, a | b)
        elif funct3 == 0b111:                           # and
            reg_write(rd, a & b)
        else:
            print(f"Error: unknown R-type funct3={funct3} funct7={funct7} at PC={hex(pc)}")
            sys.exit(1)

        return pc + 4

    # ── I-type addi / sltiu  opcode = 0010011 ────────────────────────
    elif opcode == 0b0010011:
        rd     = bits(word, 11,  7)
        funct3 = bits(word, 14, 12)
        rs1    = bits(word, 19, 15)
        imm    = sign_extend(bits(word, 31, 20), 12)

        a = registers[rs1]

        if   funct3 == 0b000:   # addi
            reg_write(rd, a + imm)
        elif funct3 == 0b011:   # sltiu
            reg_write(rd, 1 if to32u(a) < to32u(imm) else 0)
        else:
            print(f"Error: unknown I-type(0010011) funct3={funct3} at PC={hex(pc)}")
            sys.exit(1)

        return pc + 4

    # ── I-type lw  opcode = 0000011 ──────────────────────────────────
    elif opcode == 0b0000011:
        rd     = bits(word, 11,  7)
        funct3 = bits(word, 14, 12)
        rs1    = bits(word, 19, 15)
        imm    = sign_extend(bits(word, 31, 20), 12)

        if funct3 == 0b010:     # lw
            addr = to32u(registers[rs1] + imm)
            reg_write(rd, sign_extend(mem_read(addr), 32))
        else:
            print(f"Error: unsupported load funct3={funct3} at PC={hex(pc)}")
            sys.exit(1)

        return pc + 4

    # ── I-type jalr  opcode = 1100111 ────────────────────────────────
    elif opcode == 0b1100111:
        rd     = bits(word, 11,  7)
        rs1    = bits(word, 19, 15)
        imm    = sign_extend(bits(word, 31, 20), 12)

        ret_addr = pc + 4
        new_pc   = to32u(registers[rs1] + imm) & ~1   # clear LSB

        reg_write(rd, ret_addr)
        return new_pc

    # ── S-type sw  opcode = 0100011 ──────────────────────────────────
    elif opcode == 0b0100011:
        funct3   = bits(word, 14, 12)
        rs1      = bits(word, 19, 15)
        rs2      = bits(word, 24, 20)
        imm_hi   = bits(word, 31, 25)
        imm_lo   = bits(word, 11,  7)
        imm      = sign_extend((imm_hi << 5) | imm_lo, 12)

        if funct3 == 0b010:     # sw
            addr = to32u(registers[rs1] + imm)
            mem_write(addr, registers[rs2])
        else:
            print(f"Error: unsupported store funct3={funct3} at PC={hex(pc)}")
            sys.exit(1)

        return pc + 4

    # ── B-type  opcode = 1100011 ──────────────────────────────────────
    elif opcode == 0b1100011:
        funct3 = bits(word, 14, 12)
        rs1    = bits(word, 19, 15)
        rs2    = bits(word, 24, 20)

        imm12   = bits(word, 31, 31)
        imm10_5 = bits(word, 30, 25)
        imm4_1  = bits(word, 11,  8)
        imm11   = bits(word,  7,  7)

        imm_raw = (imm12 << 12) | (imm11 << 11) | (imm10_5 << 5) | (imm4_1 << 1)
        offset  = sign_extend(imm_raw, 13)

        a = registers[rs1]
        b = registers[rs2]

        # Virtual HALT: beq zero, zero, 0
        if funct3 == 0b000 and rs1 == 0 and rs2 == 0 and offset == 0:
            return None  # HALT signal

        taken = False
        if   funct3 == 0b000: taken = (a == b)                          # beq
        elif funct3 == 0b001: taken = (a != b)                          # bne
        elif funct3 == 0b100: taken = (a < b)                           # blt
        elif funct3 == 0b101: taken = (a >= b)                          # bge
        elif funct3 == 0b110: taken = (to32u(a) < to32u(b))             # bltu
        elif funct3 == 0b111: taken = (to32u(a) >= to32u(b))            # bgeu
        else:
            print(f"Error: unknown B-type funct3={funct3} at PC={hex(pc)}")
            sys.exit(1)

        return (pc + offset) if taken else (pc + 4)

    # ── U-type lui  opcode = 0110111 ─────────────────────────────────
    elif opcode == 0b0110111:
        rd  = bits(word, 11,  7)
        imm = sign_extend(bits(word, 31, 12) << 12, 32)
        reg_write(rd, imm)
        return pc + 4

    # ── U-type auipc  opcode = 0010111 ───────────────────────────────
    elif opcode == 0b0010111:
        rd  = bits(word, 11,  7)
        imm = sign_extend(bits(word, 31, 12) << 12, 32)
        reg_write(rd, pc + imm)
        return pc + 4

    # ── J-type jal  opcode = 1101111 ─────────────────────────────────
    elif opcode == 0b1101111:
        rd      = bits(word, 11,  7)
        imm20   = bits(word, 31, 31)
        imm10_1 = bits(word, 30, 21)
        imm11   = bits(word, 20, 20)
        imm19_12= bits(word, 19, 12)

        imm_raw = (imm20 << 20) | (imm19_12 << 12) | (imm11 << 11) | (imm10_1 << 1)
        offset  = sign_extend(imm_raw, 21)

        reg_write(rd, pc + 4)
        new_pc = pc + offset
        return new_pc & ~1   # clear LSB per spec

    else:
        print(f"Error: unknown opcode={bin(opcode)} at PC={hex(pc)}")
        sys.exit(1)

# ─────────────────────────────────────────────
#  Trace output helper
# ─────────────────────────────────────────────
def format_reg_line(pc):
    """
    {PC} {x0} {x1} ... {x31}  — all values as 32-bit binary strings
    """
    pc_bin   = format(to32u(pc), '032b')
    reg_bins = [format(to32u(r), '032b') for r in registers]
    return pc_bin + " " + " ".join(reg_bins)

# ─────────────────────────────────────────────
#  Main execution loop
# ─────────────────────────────────────────────
output_lines = []
pc = PROG_MEM_BASE

MAX_STEPS = 100000  # guard against infinite loops
step = 0

while step < MAX_STEPS:
    step += 1
    new_pc = decode_and_execute(pc)

    # Record state AFTER instruction executes (includes current PC for clarity)
    output_lines.append(format_reg_line(pc))

    if new_pc is None:          # HALT encountered
        break

    pc = new_pc
else:
    print("Warning: execution limit reached without HALT instruction")

# ─────────────────────────────────────────────
#  Print memory dump after HALT
#  32 locations of data memory starting at DATA_MEM_BASE
# ─────────────────────────────────────────────
for i in range(32):
    addr  = DATA_MEM_BASE + i * 4
    value = memory.get(addr, 0)
    addr_hex  = format(addr, '08x')
    value_bin = format(to32u(value), '032b')
    output_lines.append(f"0x{addr_hex}:{value_bin}")

# ─────────────────────────────────────────────
#  Write output file
# ─────────────────────────────────────────────
with open(output_file, "w") as fout:
    for line in output_lines:
        fout.write(line + "\n")

print(f"Simulation complete. {step} instruction(s) executed. Output written to '{output_file}'.")