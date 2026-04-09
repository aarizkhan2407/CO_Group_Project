import sys

#  CLI argument handling

if len(sys.argv) < 3:
    print("Usage: Simulator.py <input.bin> <output_trace.txt>")
    sys.exit(1)

input_file  = sys.argv[1]
output_file = sys.argv[2]

#  Memory layout (from spec)
#  Program mem : 0x00000000 – 0x000000FF  (256 B, 64 x 32-bit words)
#  Stack mem   : 0x00000100 – 0x0000017F  (128 B, 32 x 32-bit words)
#  Data mem    : 0x00010000 – 0x0001007F  (128 B, 32 x 32-bit words)
#  SP init     : 0x0000017C


PROG_MEM_BASE  = 0x00000000
PROG_MEM_END   = 0x000000FF
STACK_MEM_BASE = 0x00000100
STACK_MEM_END  = 0x0000017F
DATA_MEM_BASE  = 0x00010000
DATA_MEM_END   = 0x0001007F

memory    = {}
registers = [0] * 32
registers[2] = 0x0000017C   # sp  initialised per spec

output_lines = []   # trace lines collected so far

#  Error handling:
#  Spec: print error + LINE NUMBER to terminal (stdout),
#        write partial trace (no memory dump), exit.
#  Line number = instruction number in binary file = PC//4 + 1


def runtime_error(msg, pc):
    line_no = pc // 4 + 1
    print("Error at line {}: {}".format(line_no, msg))
    sys.exit(1)


#  Helpers:


def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)

def to32(value):
    value = value & 0xFFFFFFFF
    if value >= 0x80000000:
        value -= 0x100000000
    return value

def to32u(value):
    return value & 0xFFFFFFFF

def bits(word, hi, lo):
    mask = (1 << (hi - lo + 1)) - 1
    return (word >> lo) & mask



#  Memory validation
#  Only lw/sw are validated — branch/jump targets are
#  guaranteed valid by spec (errata section).
#  Valid data-access regions: stack and data memory only.



def is_valid_data_addr(addr):
    return (STACK_MEM_BASE <= addr <= STACK_MEM_END) or \
           (DATA_MEM_BASE  <= addr <= DATA_MEM_END)

def mem_write(addr, value, pc):
    addr = to32u(addr)
    if not is_valid_data_addr(addr):
        runtime_error(
            "invalid memory write at address 0x{:08x}".format(addr), pc)
    memory[addr] = to32u(value)

def mem_read_data(addr, pc):
    addr = to32u(addr)
    if not is_valid_data_addr(addr):
        runtime_error(
            "invalid memory read at address 0x{:08x}".format(addr), pc)
    return memory.get(addr, 0)

def mem_read_instr(addr):
    # Instruction fetch from program memory — no bounds check needed
    return memory.get(to32u(addr), 0)



#  Register write (x0 hardwired to 0)


def reg_write(rd, value):
    if rd != 0:
        registers[rd] = to32(value)



#  Load binary program into memory


with open(input_file, "r") as fin:
    prog_lines = [l.strip() for l in fin.readlines() if l.strip()]

if len(prog_lines) == 0:
    print("Error: input file is empty")
    sys.exit(1)

if len(prog_lines) > 64:
    print("Error: program exceeds program memory size (64 instructions max)")
    sys.exit(1)

for idx, b in enumerate(prog_lines):
    if len(b) != 32 or not all(c in '01' for c in b):
        print("Error at line {}: invalid binary word '{}'".format(idx + 1, b))
        sys.exit(1)
    memory[PROG_MEM_BASE + idx * 4] = int(b, 2)


#  Decode and execute one instruction
#  Returns new PC, or None to signal HALT


def decode_and_execute(pc):
    word   = mem_read_instr(pc)
    opcode = bits(word, 6, 0)

    # R-type  0110011 

    if opcode == 0b0110011:
        rd     = bits(word, 11,  7)
        funct3 = bits(word, 14, 12)
        rs1    = bits(word, 19, 15)
        rs2    = bits(word, 24, 20)
        funct7 = bits(word, 31, 25)
        a, b_  = registers[rs1], registers[rs2]

        if   funct3 == 0b000 and funct7 == 0b0000000: reg_write(rd, a + b_)
        elif funct3 == 0b000 and funct7 == 0b0100000: reg_write(rd, a - b_)
        elif funct3 == 0b001:                          reg_write(rd, a << (to32u(b_) & 0x1F))
        elif funct3 == 0b010:                          reg_write(rd, 1 if a < b_ else 0)
        elif funct3 == 0b011:                          reg_write(rd, 1 if to32u(a) < to32u(b_) else 0)
        elif funct3 == 0b100:                          reg_write(rd, a ^ b_)
        elif funct3 == 0b101 and funct7 == 0b0000000: reg_write(rd, to32u(a) >> (to32u(b_) & 0x1F))
        elif funct3 == 0b110:                          reg_write(rd, a | b_)
        elif funct3 == 0b111:                          reg_write(rd, a & b_)
        else:
            runtime_error("unknown R-type funct3={} funct7={}".format(funct3, funct7), pc)
        return pc + 4

    # I-type addi / sltiu  0010011

    elif opcode == 0b0010011:
        rd     = bits(word, 11,  7)
        funct3 = bits(word, 14, 12)
        rs1    = bits(word, 19, 15)
        imm    = sign_extend(bits(word, 31, 20), 12)
        a      = registers[rs1]

        if   funct3 == 0b000: reg_write(rd, a + imm)
        elif funct3 == 0b011: reg_write(rd, 1 if to32u(a) < to32u(imm) else 0)
        else:
            runtime_error("unknown I-type(0010011) funct3={}".format(funct3), pc)
        return pc + 4

    # I-type lw  0000011

    elif opcode == 0b0000011:
        rd     = bits(word, 11,  7)
        funct3 = bits(word, 14, 12)
        rs1    = bits(word, 19, 15)
        imm    = sign_extend(bits(word, 31, 20), 12)

        if funct3 == 0b010:
            addr = to32u(registers[rs1] + imm)
            reg_write(rd, sign_extend(mem_read_data(addr, pc), 32))
        else:
            runtime_error("unsupported load funct3={}".format(funct3), pc)
        return pc + 4

    # I-type jalr  1100111

    elif opcode == 0b1100111:
        rd  = bits(word, 11,  7)
        rs1 = bits(word, 19, 15)
        imm = sign_extend(bits(word, 31, 20), 12)
        # Jump target NOT validated — spec guarantees all control flow is valid

        ret_addr = pc + 4
        new_pc   = to32u(registers[rs1] + imm) & ~1
        reg_write(rd, ret_addr)
        return new_pc

    # S-type sw  0100011

    elif opcode == 0b0100011:
        funct3 = bits(word, 14, 12)
        rs1    = bits(word, 19, 15)
        rs2    = bits(word, 24, 20)
        imm    = sign_extend((bits(word, 31, 25) << 5) | bits(word, 11, 7), 12)

        if funct3 == 0b010:
            addr = to32u(registers[rs1] + imm)
            mem_write(addr, registers[rs2], pc)
        else:
            runtime_error("unsupported store funct3={}".format(funct3), pc)
        return pc + 4

    # B-type  1100011

    elif opcode == 0b1100011:
        funct3  = bits(word, 14, 12)
        rs1     = bits(word, 19, 15)
        rs2     = bits(word, 24, 20)
        imm_raw = (bits(word, 31, 31) << 12) | (bits(word,  7,  7) << 11) | \
                  (bits(word, 30, 25) <<  5) | (bits(word, 11,  8) <<  1)
        offset  = sign_extend(imm_raw, 13)
        a, b_   = registers[rs1], registers[rs2]

        # Virtual HALT: beq x0, x0, 0  — always fires, terminates simulation

        if funct3 == 0b000 and rs1 == 0 and rs2 == 0 and offset == 0:
            return None

        # Branch targets guaranteed valid by spec errata — no bounds check

        if   funct3 == 0b000: taken = (a == b_)
        elif funct3 == 0b001: taken = (a != b_)
        elif funct3 == 0b100: taken = (a < b_)
        elif funct3 == 0b101: taken = (a >= b_)
        elif funct3 == 0b110: taken = (to32u(a) < to32u(b_))
        elif funct3 == 0b111: taken = (to32u(a) >= to32u(b_))
        else:
            runtime_error("unknown B-type funct3={}".format(funct3), pc)
            taken = False
        return (pc + offset) if taken else (pc + 4)

    # U-type lui  0110111

    elif opcode == 0b0110111:
        rd  = bits(word, 11,  7)
        imm = sign_extend(bits(word, 31, 12) << 12, 32)
        reg_write(rd, imm)
        return pc + 4

    # U-type auipc  0010111

    elif opcode == 0b0010111:
        rd  = bits(word, 11,  7)
        imm = sign_extend(bits(word, 31, 12) << 12, 32)
        reg_write(rd, pc + imm)
        return pc + 4

    # J-type jal  1101111

    elif opcode == 0b1101111:
        rd      = bits(word, 11,  7)
        imm_raw = (bits(word, 31, 31) << 20) | (bits(word, 19, 12) << 12) | \
                  (bits(word, 20, 20) << 11) | (bits(word, 30, 21) <<  1)
        offset  = sign_extend(imm_raw, 21)

        # Jump target NOT validated — spec guarantees all control flow is valid

        reg_write(rd, pc + 4)
        return to32u(pc + offset) & ~1

    else:
        runtime_error("unknown opcode {}".format(bin(opcode)), pc)


# Trace format
# {PC} {x0} {x1} ... {x31}  all as 32-bit binary strings


def format_reg_line(pc):
    pc_bin   = "0b" + format(to32u(pc), '032b')
    reg_bins = ["0b" + format(to32u(r), '032b') for r in registers]

    # trailing space after last register, matching expected output format

    return " ".join([pc_bin] + reg_bins) + " "


#  Main execution loop

pc        = PROG_MEM_BASE
MAX_STEPS = 100000   # safety limit against infinite loops
step      = 0

while step < MAX_STEPS:
    step  += 1
    new_pc = decode_and_execute(pc)

    # Record state AFTER this instruction executes
    output_lines.append(format_reg_line(new_pc if new_pc is not None else pc))

    if new_pc is None:      # Virtual HALT reached — stop execution
        break

    pc = new_pc
else:
    print("Warning: execution limit reached without halt")


#  Output file:
#  1. Register trace (one line per instruction executed, including halt)
#  2. Memory dump (32 data memory locations, only after successful halt)


with open(output_file, "w") as fout:
    for line in output_lines:
        fout.write(line + "\n")

    # Memory dump after successful halt

    for i in range(32):
        addr      = DATA_MEM_BASE + i * 4
        value     = memory.get(addr, 0)
        addr_hex  = format(addr, '08X')
        value_bin = "0b" + format(to32u(value), "032b")
        fout.write("0x{}:{}\n".format(addr_hex, value_bin))

print("Simulation complete. {} instruction(s) executed. Output written to '{}'.".format(
    step, output_file))