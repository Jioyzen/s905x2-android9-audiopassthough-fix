.syntax unified
.thumb
.section .text.jf_base,"ax",%progbits
.global jf_load_bias
.type jf_load_bias,%function
.thumb_func
jf_load_bias:
.Lbias:
 adr.w r0,.Lbias
 movw r1, #:lower16:.Lbias
 movt r1, #:upper16:.Lbias
 subs r0,r0,r1
 bx lr
.global jf_original_cap
.type jf_original_cap,%function
.thumb_func
jf_original_cap:
 /* Exact displaced original get_hdmi_sink_cap prologue. */
 push.w {r4,r5,r6,r7,r8,r9,lr}
 b.w jf_cap_resume
.global jf_hbr_rate
.type jf_hbr_rate,%function
.thumb_func
jf_hbr_rate:
 /* Reached only by the existing DTS_HD/TRUEHD switch, never AC3/EAC3/core. */
 push {r2}
 movw r2,#0xee00
 movt r2,#2
 str.w r2,[r4,#0xcc]
 /* Both HBR paths use the driver's verified 131072-byte ring. */
 movs r2,#8
 str.w r2,[r4,#0xd4]
 pop {r2}
 mov.w r0,#0x8000
 mov.w r1,#0x1000
 b.w jf_hbr_resume

.global jf_source_format
.type jf_source_format,%function
.thumb_func
jf_source_format:
 push.w {r0,r1,r2,r3,r12,lr}
 mov r0,r5
 bl jf_hd_supported
 cmp r0,#0
 pop.w {r0,r1,r2,r3,r12,lr}
 beq .Loriginal_source
 mov r11,r5
 mov r7,r5
 b.w jf_source_allowed
.Loriginal_source:
 cmp.w r5,#0xa000000
 b.w jf_source_original

/* The original code divides spdifenc_get_total() by four for TrueHD.
 * MAT uses 64 bytes per 48 kHz content frame, not four. Preserve the
 * original EAC3/core arithmetic and 64-bit carry handling after this site. */
.global jf_spdif_count_shift
.type jf_spdif_count_shift,%function
.thumb_func
jf_spdif_count_shift:
 ldr.w r2,[r9,#0x1ac]
 cmp.w r2,#0xe000000
 beq .Lcount_hbr
 cmp.w r2,#0xc000000
 bne .Lcount_original
.Lcount_hbr:
 movs r6,#6
.Lcount_original:
 eor r2,r6,#0x1f
 b.w jf_count_resume

/* DELAY is in physical DMA frames (768k/s for HBR). The frame API
 * needs 48k content units. The millisecond API uses a separate /4 table. */
.global jf_latency_frames
.type jf_latency_frames,%function
.thumb_func
jf_latency_frames:
 ldr.w r5,[r4,#0x1ac]
 cmp.w r5,#0xe000000
 beq .Llatency_hbr
 cmp.w r5,#0xc000000
 bne .Llatency_original
.Llatency_hbr:
 movs r5,#16
 b.w jf_latency_resume
.Llatency_original:
 ldr.w r5,[r1,r0,lsl #2]
 b.w jf_latency_resume

/* The write path accidentally subtracts milliseconds from a frame count.
 * For HBR, call the content-frame API; retain other formats' old path. */
.global jf_presentation_latency
.type jf_presentation_latency,%function
.thumb_func
jf_presentation_latency:
 ldr.w r1,[r0,#0x1ac]
 cmp.w r1,#0xe000000
 beq .Lcontent_latency
 cmp.w r1,#0xc000000
 bne .Llegacy_latency
.Lcontent_latency:
 b.w jf_original_latency_frames
.Llegacy_latency:
 b.w jf_original_latency_ms

.global jf_truehd_pause
.type jf_truehd_pause,%function
.thumb_func
jf_truehd_pause:
 ldr.w r0,[r6,#0x1ac]
 cmp.w r0,#0xe000000
 bne .Lpause_legacy
 push.w {r1,r2,r3,r5,r12,lr}
 ldr.w r0,[r6,#0x108]
 movs r1,#1
 bl jf_truehd_pcm_pause
 pop.w {r1,r2,r3,r5,r12,lr}
 mov r7,r0
 cmp r0,#0
 blt .Lpause_error
 b.w jf_pause_done
.Lpause_error:
 b.w jf_pause_error
.Lpause_legacy:
 ldr.w r0,[r6,#0x108]
 b.w jf_pause_legacy

.global jf_truehd_resume
.type jf_truehd_resume,%function
.thumb_func
jf_truehd_resume:
 ldr.w r0,[r4,#0x1ac]
 cmp.w r0,#0xe000000
 bne .Lresume_legacy
 push.w {r1,r2,r3,r5,r12,lr}
 ldr.w r0,[r4,#0x108]
 movs r1,#0
 bl jf_truehd_pcm_pause
 pop.w {r1,r2,r3,r5,r12,lr}
 b.w jf_resume_result
.Lresume_legacy:
 ldr.w r0,[r4,#0x108]
 b.w jf_resume_legacy

/* AUGE pause/prepare cannot preserve a TrueHD MAT ring. Plain DIRECT
 * and DTS streams use AudioFlinger's standard software pause/standby fallback.
 * Keep mandatory hardware pause for HW_AV_SYNC, and all other codecs.
 * r0's CMP flags at the displaced site are live until 0x15052. */
.global jf_pause_capability
.type jf_pause_capability,%function
.thumb_func
jf_pause_capability:
 push {r12}
 ldr.w r12,[r7,#0x1ac]
 cmp.w r12,#0xe000000
 beq .Lraw_pause_cap
 cmp.w r12,#0xc000000
 beq .Lraw_pause_cap
 cmp.w r12,#0xb000000
 bne .Lnative_pause_cap
.Lraw_pause_cap:
 tst.w r8,#0x40
 bne .Lnative_pause_cap
 strd r6,r6,[r7,#0x50]
 b .Lpause_cap_done
.Lnative_pause_cap:
 strd r3,r2,[r7,#0x50]
.Lpause_cap_done:
 pop {r12}
 cmp r0,#0
 b.w jf_pause_cap_resume

.global jf_dts_write_probe
.type jf_dts_write_probe,%function
.thumb_func
jf_dts_write_probe:
 push.w {r0,r1,r2,r3,r12,lr}
 mov r0,r9
 mov r1,r10
 mov r2,r5
 bl jf_dts_prepare
 pop.w {r0,r1,r2,r3,r12,lr}
 ldr.w r0,[r9,#0x1ac]
 str r0,[sp,#0x54]
 /* Displaced original standby load. */
 ldrb.w r0,[r9,#0x118]
 b.w jf_dts_write_resume
