import sys

if ( len(sys.argv) )!=3:
    print("Usage: assembler.py <input.asm> <output.bin>")

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

def R_encode(operation, rd, rs1, rs2):
    funct7, funct3, opcode= R_type[operation]
    print(funct7+Register_file[rs2]+Register_file[rs1]+funct3+Register_file[rd]+opcode)

def throw_error(msg, lineno):
    print(f"Error at lineno {lineno}: {msg}")
    sys.exit(1)

with open(input_file, 'r') as fin:
    PC= 0
    labels= {}
    lines= fin.readlines
    for lineno, line in enumerate(lines):
        lineno= lineno+1
        line= line.strip()
        if (not line):
            continue
        if(":" in line):
            label, inst= line.split(":")
            labels[label.strip()]= PC
            line= inst.strip()
            if (not line):
                PC+=4
                continue
    
    print(lineno, line)
    PC+=4

with open(output_file, "w") as fout:
    fout.write("")