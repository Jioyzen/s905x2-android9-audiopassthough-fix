.syntax unified
.thumb
.text
.balign 2
.global entry
.thumb_func
entry:
 push.w {r0,r1,r2,r3,r12,lr}
 ldr.w r12,[sp,#0x20]
 cmp.w r12,#0xb000000
 beq compressed
 cmp.w r12,#0xc000000
 beq compressed
 cmp.w r12,#0xe000000
 bne original
compressed:
 ldr.w r12,[sp,#0x38]
 cmp.w r12,#0
 beq original
 ldr.w r12,[r12]
 cmp.w r12,#0
 bne original
 ldr.w r12,[sp,#0x40]
 cmp.w r12,#0
 beq original
 ldr.w r12,[r12]
 tst.w r12,#0x50
 bne original
 ldr r1,[sp,#0x28]
 cbz r1,original
 ldr r2,[r1]
 cmp.w r2,#0x20000
 bhs original
 mov.w r2,#0x20000
 str r2,[r1]
original:
 pop.w {r0,r1,r2,r3,r12,lr}
 push.w {r4,r5,r6,r7,r8,r9,r10,r11,lr}
 b.w resume
