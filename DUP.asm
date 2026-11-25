// Dup.asm - duplicate label test
(LOOP)
@1
D=A
(LOOP)
@LOOP
0;JMP
 
