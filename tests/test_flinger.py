from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
import struct,json
R=Path(__file__).resolve().parents[1]/'build/flinger';bias=0x51000000;cases=[]
for fmt in [1,0x9000000,0xa000000,0xb000000,0xc000000,0xe000000]:
 for old in [0,4104,65536,131072,262144]:
  for flags in [0,1,0x41,0x11]:
   for shared in [False,True]:
    m=Uc(UC_ARCH_ARM,UC_MODE_THUMB);m.mem_map(bias,0x80000);m.mem_map(0x1000000,0x10000);m.mem_map(0x2000000,0x10000)
    with (R/'libaudioflinger.so').open('rb') as f:
     for p in ELFFile(f).iter_segments():
      if p['p_type']=='PT_LOAD':m.mem_write(bias+p['p_vaddr'],p.data())
    sp=0x1008000;m.reg_write(UC_ARM_REG_SP,sp)
    for off,val in [(8,fmt),(16,0x2000000),(32,0x2000010),(40,0x2000020)]:m.mem_write(sp+off,struct.pack('<I',val))
    for ptr,val in [(0x2000000,old),(0x2000010,int(shared)),(0x2000020,flags)]:m.mem_write(ptr,struct.pack('<I',val))
    registers=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12,UC_ARM_REG_LR]
    values=[0x123400+i*16 for i in range(len(registers))]
    for reg,val in zip(registers,values):m.reg_write(reg,val)
    m.hook_add(UC_HOOK_CODE,lambda m,a,s,u:m.emu_stop() if a==bias+0x1df3c else None)
    m.emu_start(bias+0x1df38+1,bias+0x80000,count=100)
    want=max(old,131072) if fmt in [0xb000000,0xc000000,0xe000000] and not shared and not flags&0x50 else old
    assert struct.unpack('<I',m.mem_read(0x2000000,4))[0]==want,(hex(fmt),old,flags,shared)
    assert m.reg_read(UC_ARM_REG_SP)==sp-36
    for reg,val in zip(registers,values):assert m.reg_read(reg)==val
    cases.append([hex(fmt),old,flags,shared,want])
(R/'flinger-tests.json').write_text(json.dumps({'passed_cases':len(cases),'audio_output_performed':False,'cases':cases},indent=2)+'\n');print('AudioFlinger ARM ABI/buffer tests passed:',len(cases))
