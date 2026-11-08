from pathlib import Path
import struct,subprocess,hashlib,json
from common import ROOT, ndk_bin
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
R=ROOT;src=R/'baseline/rootfs/vendor/lib/hw/audio.primary.amlogic.so';out=R/'build';out.mkdir(parents=True,exist_ok=True);tools=ndk_bin()
raw=bytearray(src.read_bytes());assert len(raw)==510788 and hashlib.sha256(raw).hexdigest()=='a436ebedcc7a6bde906d544b7d36b9faa8963fd792e1b2c416902c135b5e4c70'
with src.open('rb') as f:
 e=ELFFile(f);loads=[p for p in e.iter_segments() if p['p_type']=='PT_LOAD'];addr=(max(p['p_vaddr']+p['p_memsz'] for p in loads)+4095)&~4095
 notes=[i for i,p in enumerate(e.iter_segments()) if p['p_type']=='PT_NOTE'];assert len(notes)==1
 note=notes[0];phoff=e.header['e_phoff']+note*e.header['e_phentsize']
assert raw[0x2287c:0x22880]==bytes.fromhex('2de9f043')
assert raw[0x1b5c6:0x1b5ca]==bytes.fromhex('4ff48040')
assert raw[0x283dc:0x283e0]==bytes.fromhex('b5f1206f')
assert raw[0x191b6:0x191ba]==bytes.fromhex('86f01f02')
assert raw[0x193d2:0x193d6]==bytes.fromhex('02f06dfa')
assert raw[0x215f0:0x215f4]==bytes.fromhex('51f82050')
assert struct.unpack_from('<I',raw,0x7797c)[0]==1
assert raw[0x1a976:0x1a97a]==bytes.fromhex('d6f80801')
assert raw[0x18a94:0x18a98]==bytes.fromhex('99f81801')
assert raw[0x1502c:0x15030]==bytes.fromhex('c7e91432')
assert raw[0x1aad6:0x1aada]==bytes.fromhex('d4f80801')
(out/'hooks.ld').write_text('SECTIONS { . = '+hex(addr)+'; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }')
def run(args):subprocess.run([str(x) for x in args],check=True,capture_output=True)
cc=tools/'armv7a-linux-androideabi28-clang'
run([cc,'-Os','-mthumb','-fPIC','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-c',R/'src/hal/hal_channels.c','-o',out/'hal-channels.o'])
run([cc,'-c',R/'src/hal/hal_hooks.S','-o',out/'hal-hooks.o'])
run([tools/'ld.lld','-m','armelf_linux_eabi','-T',out/'hooks.ld','--defsym=jf_cap_resume=0x22880','--defsym=jf_hbr_resume=0x1b5ce','--defsym=jf_source_original=0x283e0','--defsym=jf_source_allowed=0x28412','--defsym=jf_count_resume=0x191ba','--defsym=jf_latency_resume=0x215f4','--defsym=jf_original_latency_frames=0x215c4','--defsym=jf_original_latency_ms=0x1b8b0','--defsym=jf_pause_done=0x1a9b0','--defsym=jf_pause_error=0x1a9b8','--defsym=jf_pause_legacy=0x1a97a','--defsym=jf_resume_result=0x1ab22','--defsym=jf_resume_legacy=0x1aada','--defsym=jf_pause_cap_resume=0x15030','--defsym=jf_dts_write_resume=0x18a98','-o',out/'hooks.elf',out/'hal-channels.o',out/'hal-hooks.o'])
run([tools/'llvm-objcopy','-O','binary','--only-section=.text',out/'hooks.elf',out/'hooks.bin'])
with (out/'hooks.elf').open('rb') as f:
 e=ELFFile(f);sym={s.name:s['st_value']&~1 for s in e.get_section_by_name('.symtab').iter_symbols() if s.name}
# Assemble each four-byte branch at its actual old virtual address.
patches=[]
for where,dest,branch in [(0x2287c,sym['jf_sink_cap'],'b.w'),(0x1b5c6,sym['jf_hbr_rate'],'b.w'),(0x283dc,sym['jf_source_format'],'b.w'),(0x191b6,sym['jf_spdif_count_shift'],'b.w'),(0x193d2,sym['jf_presentation_latency'],'bl'),(0x215f0,sym['jf_latency_frames'],'b.w'),(0x1a976,sym['jf_truehd_pause'],'b.w'),(0x1aad6,sym['jf_truehd_resume'],'b.w'),(0x1502c,sym['jf_pause_capability'],'b.w'),(0x18a94,sym['jf_dts_write_probe'],'b.w')]:
 a=out/f'branch-{where:x}.S';a.write_text('.syntax unified\n.thumb\n.section .patch,\"ax\",%progbits\n.balign 2\n.global entry\n.thumb_func\nentry:\n '+branch+' target\n')
 run([cc,'-c',a,'-o',a.with_suffix('.o')]);run([tools/'ld.lld','-m','armelf_linux_eabi','--section-start=.patch='+hex(where),'--defsym=target='+hex(dest),'-e','entry',a.with_suffix('.o'),'-o',a.with_suffix('.elf')]);run([tools/'llvm-objcopy','-O','binary','--only-section=.patch',a.with_suffix('.elf'),a.with_suffix('.bin')])
 code=a.with_suffix('.bin').read_bytes();assert len(code)==4
 ins=list(Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(code,where));assert len(ins)==1 and int(ins[0].op_str.lstrip('#'),16)==dest,(ins[0].op_str,hex(dest))
 patches.append({'vaddr':hex(where),'before':raw[where:where+4].hex(),'after':code.hex(),'destination':hex(dest)});raw[where:where+4]=code
# Shared table feeds the millisecond API at nominal 192k: HBR physical
# delay must first be /4. The content-frame API is separately /16 above.
raw[0x7797c:0x77980]=struct.pack('<I',4)
patches.append({'vaddr':'0x7797c','before':'01000000','after':'04000000','purpose':'TrueHD ALSA delay /4 before converting at nominal 192k'})
blob=(out/'hooks.bin').read_bytes();offset=(len(raw)+4095)&~4095;raw.extend(b'\0'*(offset-len(raw)));raw.extend(blob)
# Reuse the nonessential PT_NOTE header; keep every original load VA/offset intact.
raw[phoff:phoff+32]=struct.pack('<8I',1,offset,addr,addr,len(blob),len(blob),5,4096)
(out/'audio.primary.amlogic.so').write_bytes(raw)
info={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'sha256':hashlib.sha256(raw).hexdigest(),'new_load_vaddr':hex(addr),'new_load_file_offset':hex(offset),'new_load_bytes':len(blob),'patches':patches,'symbols':{k:hex(v) for k,v in sym.items() if k.startswith('jf_')}}
(out/'hal-patch.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2))
