from pathlib import Path
from elftools.elf.elffile import ELFFile
import struct,hashlib,subprocess,json
from common import ROOT, ndk_bin
R=ROOT/'build/flinger';R.mkdir(parents=True,exist_ok=True);T=ndk_bin();src=ROOT/'baseline/rootfs/system/lib/libaudioflinger.so';b=bytearray(src.read_bytes())
assert hashlib.sha256(b).hexdigest()=='b3fec98c77e404ea3d84ef47ef142732122340ea9da0339f5920a9f458766f17'
assert b[0x17f38:0x17f3c]==bytes.fromhex('2de9f04f')
with src.open('rb') as f:
 e=ELFFile(f);addr=(max(s['p_vaddr']+s['p_memsz'] for s in e.iter_segments() if s['p_type']=='PT_LOAD')+4095)&~4095
 idx=[i for i,s in enumerate(e.iter_segments()) if s['p_type']=='PT_NOTE'];assert len(idx)==1
 phoff=e.header['e_phoff']+idx[0]*e.header['e_phentsize']
# ARM32 non-trivial sp<Track> return uses hidden R0, this R1/client R2/type R3.
# Original stack: attr +0, pSampleRate +4, format +8, channelMask +12,
# pFrameCount +16, pNotificationFrameCount +20, sharedBuffer ref +32,
# flags pointer +40. Verified against local disassembly, not A12 offsets.
asm=(ROOT/'src/flinger/flinger_buffer.S').read_text()
(R/'flinger_buffer.S').write_text(asm)
def run(a):subprocess.run([str(x) for x in a],check=True,capture_output=True)
cc=T/'armv7a-linux-androideabi28-clang';run([cc,'-c',R/'flinger_buffer.S','-o',R/'flinger-buffer.o']);run([T/'ld.lld','-m','armelf_linux_eabi','-Ttext='+hex(addr),'--defsym=resume=0x1df3c','-e','entry',R/'flinger-buffer.o','-o',R/'flinger-buffer.elf']);run([T/'llvm-objcopy','-O','binary','--only-section=.text',R/'flinger-buffer.elf',R/'flinger-buffer.bin'])
(R/'flinger-branch.S').write_text('.syntax unified\n.thumb\n.section .patch,"ax",%progbits\n.global entry\n.thumb_func\nentry: b.w target\n');run([cc,'-c',R/'flinger-branch.S','-o',R/'flinger-branch.o']);run([T/'ld.lld','-m','armelf_linux_eabi','--section-start=.patch=0x1df38','--defsym=target='+hex(addr),'-e','entry',R/'flinger-branch.o','-o',R/'flinger-branch.elf']);run([T/'llvm-objcopy','-O','binary','--only-section=.patch',R/'flinger-branch.elf',R/'flinger-branch.bin'])
branch=(R/'flinger-branch.bin').read_bytes();assert len(branch)==4;b[0x17f38:0x17f3c]=branch
blob=(R/'flinger-buffer.bin').read_bytes();off=(len(b)+4095)&~4095;b.extend(b'\0'*(off-len(b)));b.extend(blob);b[phoff:phoff+32]=struct.pack('<8I',1,off,addr,addr,len(blob),len(blob),5,4096)
(R/'libaudioflinger.so').write_bytes(b);info={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'sha256':hashlib.sha256(b).hexdigest(),'patch_vaddr':'0x1df38','patch_file_offset':'0x17f38','branch':branch.hex(),'new_vaddr':hex(addr),'new_file_offset':hex(off),'payload_bytes':len(blob),'minimum_encoded_frame_count':131072,'formats':['DTS','DTS_HD','DOLBY_TRUEHD'],'exclude':'static shared buffers, HW_AV_SYNC, COMPRESS_OFFLOAD'};(R/'flinger-patch.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2))
