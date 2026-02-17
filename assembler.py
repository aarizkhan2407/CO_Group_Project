import sys

if ( len(sys.argv) )!=3:
    print("Usage: assembler.py <input.asm> <output.bin>")
    sys.exit(1)

input_file= sys.argv[1]
output_file= sys.argv[2]

Register_file= {
    "zero": "00000",
    "ra":   "00001",
    "sp":   "00010",
    "s0":   "01000",
    "s1":   "01001",
    "s2":   "10010",
    "s3":   "10011",
}

R_type= {
    "add":  ("0000000", "000", "0110011"),
    "sub":  ("0100000", "000", "0110011"),
    "sll":  ("0000000", "001", "0110011"),
    "slt":  ("0000000", "010", "0110011"),
    "sltu": ("0000000", "011", "0110011"),
    "xor":  ("0000000", "100", "0110011"),
    "srl":  ("0000000", "101", "0110011"),
    "or":   ("0000000", "110", "0110011"),
    "and":  ("0000000", "111", "0110011"),
}

I_type = {
    "addi":  ("000", "0010011"),
    "lw":    ("010", "0000011"),
    "sltiu": ("011", "0010011"),
    "jalr":  ("000", "1100111")
}


def R_encode(operation, rd, rs1, rs2):
    funct7, funct3, opcode= R_type[operation]
    print(funct7+Register_file[rs2]+Register_file[rs1]+funct3+Register_file[rd]+opcode)

def throw_error(msg, lineno):
    print(f"Error at lineno {lineno}: {msg}")
    sys.exit(1)

def BinaryEncoding(value, bits):

    if (value < 0):
        value= (1<<bits) + value
    return format(value, f'0{bits}b')

with open(output_file, "w") as fout:

    PC = 0

    with open(input_file, 'r') as fin:
        lines = fin.readlines()

    for lineno, line in enumerate(lines, start=1):

        line = line.strip()

        if not line:
            continue

        line = line.replace(",", " ")
        parts = line.split()

        operation = parts[0]

        # R-TYPE
        if operation in R_type:

            if len(parts) != 4:
                throw_error("Invalid operand count", lineno)

            rd, rs1, rs2 = parts[1], parts[2], parts[3]

            binary = (
                R_type[operation][0]
                + Register_file[rs2]
                + Register_file[rs1]
                + R_type[operation][1]
                + Register_file[rd]
                + R_type[operation][2]
            )

            fout.write(binary + "\n")

        # I-TYPE
        elif operation in I_type:

            if len(parts) != 4:
                throw_error("Invalid operand count", lineno)

            rd = parts[1]
            rs1 = parts[2]
            imm = int(parts[3])

            imm_bin = BinaryEncoding(imm, 12)

            funct3, opcode = I_type[operation]

            binary = (
                imm_bin
                + Register_file[rs1]
                + funct3
                + Register_file[rd]
                + opcode
            )

            fout.write(binary + "\n")

        else:
            throw_error("Invalid instruction", lineno)

        PC += 4




