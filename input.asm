# ---- U-Type instructions ----
lui s1,10
auipc s2,5

# ---- I-Type instructions ----
addi s3,s1,4
sltiu s4,s3,8

# ---- R-Type instructions ----
add s5,s3,s4
sub s6,s5,s3
and s7,s5,s4
or s8,s7,s3

# ---- Memory instructions ----
sw s5,0(sp)
lw s9,0(sp)

# ---- Branch instructions ----
beq s5,s9,equal
addi s10,s10,1

equal:
addi s11,s11,2

# ---- Backward branch ----
bne s11,s10,start

start:
addi s1,s1,1

# ---- Jump instruction ----
jal ra,end

addi s2,s2,1   # should still be encoded even though jump occurs

end:
add s3,s3,s3

beq zero,zero,0