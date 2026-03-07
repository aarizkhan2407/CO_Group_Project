import sys

if ( len(sys.argv) )!=3:
    print("Usage: assembler.py <input.asm> <output.bin>")
    sys.exit(1)

input_file= sys.argv[1]
output_file= sys.argv[2]

Register_file = {
    "zero": "00000",
    "ra":   "00001",
    "sp":   "00010",
    "gp":   "00011",
    "tp":   "00100",

    "t0": "00101",
    "t1": "00110",
    "t2": "00111",

    "s0": "01000",
    "s1": "01001",

    "a0": "01010",
    "a1": "01011",
    "a2": "01100",
    "a3": "01101",
    "a4": "01110",
    "a5": "01111",
    "a6": "10000",
    "a7": "10001",

    "s2":  "10010",
    "s3":  "10011",
    "s4":  "10100",
    "s5":  "10101",
    "s6":  "10110",
    "s7":  "10111",
    "s8":  "11000",
    "s9":  "11001",
    "s10": "11010",
    "s11": "11011",

    "t3": "11100",
    "t4": "11101",
    "t5": "11110",
    "t6": "11111",
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

S_type = {
    "sw": ("010", "0100011")
}

B_type = {
    "beq":  ("000", "1100011"),
    "bne":  ("001", "1100011"),
    "blt":  ("100", "1100011"),
    "bge":  ("101", "1100011"),
    "bltu": ("110", "1100011"),
    "bgeu": ("111", "1100011")
}

U_type = {
    "lui": "0110111",
    "auipc": "0010111"
}

J_type = {
    "jal": "1101111"
}

def throw_error(msg, lineno):
    print(f"Error at lineno {lineno}: {msg}")
    sys.exit(1)

def BinaryEncoding(value, bits):

    if (value < 0):
        value= (1<<bits) + value
    return format(value, f'0{bits}b')

labels = {}
PC = 0

with open(input_file, "r") as fin:
    lines = fin.readlines()

for lineno, line in enumerate(lines):    #First pass
    lineno+=1
                        #Finding all labels and put them in dict labels
    line = line.split("#")[0].strip()

    if not line:
        continue

    if ":" in line:
        label, rest = line.split(":",1)
        label= label.strip()

        if label in labels:
            throw_error("Duplicate labels", lineno)
        
        labels[label] = PC
        line = rest.strip()

        if not line:
            continue

    PC+=4

with open(output_file, "w") as fout:

    PC = 0

    for lineno, line in enumerate(lines):
        lineno+=1

        line = line.split("#")[0].strip()

        if not line:
            continue

        if ":" in line:
            label, line = line.split(":", 1)

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
            
            funct3, opcode = I_type[operation]

            if operation == "addi" or operation=="sltiu":
                rd = parts[1]
                rs1 = parts[2]
                imm = int(parts[3])
            
            elif operation == "jalr" or operation == "lw":
                rd = parts[1]
                imm_rs1 = parts[2]
                imm_str, rs1_str = imm_rs1.split("(")
                imm = int(imm_str)
                
                rs1 = rs1_str.replace(")", "")

            imm_bin = BinaryEncoding(imm, 12)

            binary = (
                imm_bin
                + Register_file[rs1]
                + funct3
                + Register_file[rd]
                + opcode
                )
                
            fout.write(binary + "\n")
        
        # S-TYPE
        elif operation in S_type:

            funct3, opcode = S_type[operation]

            rs2 = parts[1]
            imm_rs1 = parts[2]

            str_imm, rs1_str = imm_rs1.split("(")
            imm = int(str_imm)

            rs1 = rs1_str.replace(")", "")

            imm_bin = BinaryEncoding(imm, 12)

            upper_imm = imm_bin[:7]
            lower_imm = imm_bin[7:]

            binary = (
                upper_imm
                + Register_file[rs2]
                + Register_file[rs1]
                + funct3
                + lower_imm
                + opcode
                )
            
            fout.write(binary + "\n")
        
        # B-TYPE
        elif operation in B_type:

            if len(parts)!=4:
                throw_error("Invalid operand count", lineno)

            funct3, opcode = B_type[operation]

            rs1 = parts[1]
            rs2 = parts[2]
            label = parts[3]

            if label not in labels:
                throw_error("Undefined label", lineno)
            
            target = labels[label]

            offset = target - PC
            imm = BinaryEncoding(offset, 13)

            imm12 = imm[0]
            imm10_5 = imm[2:7]
            imm4_1 = imm[7:11]
            imm11 = imm[1]

            binary = (
                imm12
            + imm10_5
            + Register_file[rs2]
            + Register_file[rs1]
            + funct3
            + imm4_1
            + imm11
            + opcode
            )

            fout.write(binary + "\n")

        elif operation in U_type:
            
            if len(parts) != 3:
                throw_error("Invalid operand count", lineno)
                
                rd = parts[1]
                
                if rd not in Register_file:
                    throw_error("Invalid register", lineno)
                    
                imm = int(parts[2])
                imm_bin = BinaryEncoding(imm, 20)
                
                opcode = U_type[operation]
                binary = (
                    imm_bin
                    + Register_file[rd]
                    + opcode
                    )
                
                fout.write(binary + "\n")

        elif operation in  J_type:

            if len(parts)!=3:
                throw_error("Invalid operand count", lineno)

            rd = parts[1]
            label = parts[2]

            if rd not in Register_file:
                throw_error("Invalid Register", lineno)

            if label not in labels:
                throw_error("Inavlid label", lineno)

            target = labels[label]
            offest = target - PC

            imm_bin = BinaryEncoding(offset, 21)

            imm20 = imm_bin[20]
            imm19_12 = imm_bin[1:9]
            imm11 = imm_bin[9]
            imm10_1 = imm_bin[10:20]

            opcode = J_type[operation]

            binary = (
                imm20
            + imm10_1
            + imm11
            + imm19_12
            + Register_file[rd]
            + opcode
            )

            fout.write(binary+"\n")

        else:
            throw_error("Invalid instruction", lineno)

        PC += 4

