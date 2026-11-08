from pathlib import Path
import json,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[1]
info=json.loads((R/'build/hal-patch.json').read_text());symbols={k:int(v,16) for k,v in info['symbols'].items()};bias=0x51000000

def machine():
 m=Uc(UC_ARCH_ARM,UC_MODE_THUMB);m.mem_map(bias,0x90000);m.mem_map(0x1000000,0x10000);m.mem_map(0x2000000,0x20000)
 with (R/'build/audio.primary.amlogic.so').open('rb') as f:
  e=ELFFile(f)
  for p in e.iter_segments():
   if p['p_type']=='PT_LOAD':m.mem_write(bias+p['p_vaddr'],p.data())
 m.reg_write(UC_ARM_REG_SP,0x1008000)
 return m
results=[]
for fmt in [0xc000000,0xe000000]:
 m=machine();m.reg_write(UC_ARM_REG_R4,0x2000000);m.reg_write(UC_ARM_REG_R2,0x12345678)
 m.mem_write(0x2000000+0x1ac,struct.pack('<I',fmt))
 m.mem_write(0x2000000+0xd4,struct.pack('<I',4))
 m.hook_add(UC_HOOK_CODE,lambda m,a,s,u:m.emu_stop() if a==bias+0x1b5ce else None)
 m.emu_start(bias+0x1b5c6+1,bias+0x90000,count=200)
 assert struct.unpack('<I',m.mem_read(0x2000000+0xcc,4))[0]==192000
 assert m.reg_read(UC_ARM_REG_R2)==0x12345678 and m.reg_read(UC_ARM_REG_SP)==0x1008000
 assert m.reg_read(UC_ARM_REG_R0)==32768
 assert m.reg_read(UC_ARM_REG_R1)==4096
 assert struct.unpack('<I',m.mem_read(0x2000000+0xd4,4))[0]==8
results.append('HBR 192k; TrueHD/DTS-HD buffer 32768 physical frames; scratch/stack preserved')
for allowed in [False,True]:
 for fmt in [1,0x9000000,0xa000000,0xb000000,0xc000000,0xe000000,0x12345678]:
  m=machine();m.reg_write(UC_ARM_REG_R5,fmt);m.reg_write(UC_ARM_REG_R7,0xa000000)
  def hook(m,a,s,u):
   if a==bias+0x28412:m.emu_stop()
   elif a==bias+symbols['jf_hd_supported']:
    m.reg_write(UC_ARM_REG_R0,int(allowed and fmt in (0xc000000,0xe000000)));m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
   elif a==bias+0xc3d8:m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  m.hook_add(UC_HOOK_CODE,hook);m.emu_start(bias+0x283dc+1,bias+0x90000,count=500)
  expected=fmt if fmt in (1,0x9000000,0xa000000,0xb000000) or (allowed and fmt in (0xc000000,0xe000000)) else 1
  assert m.reg_read(UC_ARM_REG_R11)==expected,(allowed,hex(fmt),hex(m.reg_read(UC_ARM_REG_R11)),hex(m.reg_read(UC_ARM_REG_PC)))
  assert m.reg_read(UC_ARM_REG_SP)==0x1008000
results.append('Source whitelist: 14 supported/unsupported format cases preserve legacy behavior and admit HD only with EDID support')
for fmt,legacy_shift,divisor in [(1,2,4),(0x9000000,2,4),(0xa000000,4,16),(0xb000000,2,4),(0xc000000,2,64),(0xe000000,2,64)]:
 for total in [0,1,61440,61440*50,(1<<36)+61440,(1<<60)+123456789]:
  m=machine();m.reg_write(UC_ARM_REG_R9,0x2000000);m.reg_write(UC_ARM_REG_R6,legacy_shift)
  m.reg_write(UC_ARM_REG_R0,total&0xffffffff);m.reg_write(UC_ARM_REG_R1,total>>32)
  m.mem_write(0x2000000+0x1ac,struct.pack('<I',fmt));m.mem_write(0x2000000+0x148,struct.pack('<Q',12345))
  m.hook_add(UC_HOOK_CODE,lambda m,a,s,u:m.emu_stop() if a==bias+0x191d4 else None)
  m.emu_start(bias+0x191b6+1,bias+0x90000,count=200)
  result=struct.unpack('<Q',m.mem_read(0x2000000+0x130,8))[0]
  assert result==total//divisor+12345,(hex(fmt),total,result)
  assert m.reg_read(UC_ARM_REG_SP)==0x1008000
results.append('36 64-bit SPDIF counter cases: TrueHD/DTS-HD /64 plus stream baseline; core/EAC3 unchanged, no 32-bit truncation')
for fmt,index,expected in [(0xa000000,0,4),(0xb000000,2,1),(0xc000000,4,16),(0xe000000,3,16)]:
 m=machine();m.reg_write(UC_ARM_REG_R4,0x2000000);m.reg_write(UC_ARM_REG_R0,index);m.reg_write(UC_ARM_REG_R1,bias+0x77970)
 m.mem_write(0x2000000+0x1ac,struct.pack('<I',fmt))
 m.hook_add(UC_HOOK_CODE,lambda m,a,s,u:m.emu_stop() if a==bias+0x215f4 else None)
 m.emu_start(bias+0x215f0+1,bias+0x90000,count=100)
 assert m.reg_read(UC_ARM_REG_R5)==expected
 assert m.reg_read(UC_ARM_REG_R0)==index and m.reg_read(UC_ARM_REG_R1)==bias+0x77970
results.append('Latency frame hook converts HBR /16; independent millisecond table is /4 at 192k')
for fmt in [1,0x9000000,0xa000000,0xb000000,0xc000000,0xe000000]:
 m=machine();m.reg_write(UC_ARM_REG_R0,0x2000000);m.mem_write(0x2000000+0x1ac,struct.pack('<I',fmt))
 reached=[]
 def h(m,a,s,u):
  if a in [bias+0x215c4,bias+0x1b8b0]:reached.append(a);m.emu_stop()
 m.hook_add(UC_HOOK_CODE,h);m.emu_start(bias+0x193d2+1,bias+0x90000,count=100)
 assert reached==[bias+(0x215c4 if fmt in [0xc000000,0xe000000] else 0x1b8b0)]
 assert m.reg_read(UC_ARM_REG_LR)==bias+0x193d7 and m.reg_read(UC_ARM_REG_R0)==0x2000000
results.append('HBR presentation subtracts content frames instead of milliseconds; other formats keep original call and LR')
for state in [1,2,3,4,5,6,7]:
 for pause in [0,1]:
  m=machine();m.reg_write(UC_ARM_REG_R0,0x2001000);m.reg_write(UC_ARM_REG_R1,pause);m.reg_write(UC_ARM_REG_LR,bias+0x8ff01)
  calls=[]
  def ctl(m,a,s,u):
   if a==bias+0x8ff00:m.emu_stop()
   elif a==bias+0xcdbc:
    cmd=m.reg_read(UC_ARM_REG_R1);arg=m.reg_read(UC_ARM_REG_R2);calls.append((cmd,arg))
    if cmd==0x806c4120:m.mem_write(arg,struct.pack('<I',state))
    m.reg_write(UC_ARM_REG_R0,0);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  m.hook_add(UC_HOOK_CODE,ctl);m.emu_start(bias+symbols['jf_truehd_pcm_pause']+1,bias+0x90000,count=2000)
  expected=[]
  if pause:
   if state not in [2,4,6]:expected=[(0x40044145,1)]
  elif state==6:expected=[(0x40044145,0)]
  elif state not in [2,3,5]:expected=[(0x4140,None)]
  assert calls[0][0]==0x806c4120
  assert [x[0] for x in calls[1:]]==[x[0] for x in expected],(state,pause,calls)
  if expected and expected[0][1] is not None:assert calls[1][1]==expected[0][1]
  assert m.reg_read(UC_ARM_REG_R0)==0 and m.reg_read(UC_ARM_REG_SP)==0x1008000
results.append('14 PCM pause/resume states: never PREPARE an existing prepared/running MAT ring; PAUSED resumes without reset; XRUN recovers')
for fmt in [1,0x9000000,0xa000000,0xb000000,0xc000000,0xe000000]:
 for pause in [False,True]:
  m=machine();m.reg_write(UC_ARM_REG_R4,0x2000000);m.reg_write(UC_ARM_REG_R6,0x2000000)
  m.mem_write(0x2000000+0x1ac,struct.pack('<I',fmt));m.mem_write(0x2000000+0x108,struct.pack('<I',0x2001000))
  reached=[]
  def route(m,a,s,u):
   if a==bias+symbols['jf_truehd_pcm_pause']:
    assert m.reg_read(UC_ARM_REG_R0)==0x2001000 and m.reg_read(UC_ARM_REG_R1)==int(pause)
    m.reg_write(UC_ARM_REG_R0,0);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
   elif a in [bias+0x1a9b0,bias+0x1a97a,bias+0x1ab22,bias+0x1aada]:reached.append(a);m.emu_stop()
  m.hook_add(UC_HOOK_CODE,route);m.emu_start(bias+(0x1a976 if pause else 0x1aad6)+1,bias+0x90000,count=1000)
  expected=(0x1a9b0 if pause else 0x1ab22) if fmt==0xe000000 else (0x1a97a if pause else 0x1aada)
  assert reached==[bias+expected] and m.reg_read(UC_ARM_REG_SP)==0x1008000
results.append('Pause/resume supplement is TrueHD-only; 10 other format paths retain original targets')

for fmt in [1,0x9000000,0xa000000,0xb000000,0xc000000,0xe000000]:
 for flags in [1,0x41]:
  for r0 in [0,1]:
   m=machine();m.reg_write(UC_ARM_REG_R0,r0);m.reg_write(UC_ARM_REG_R7,0x2000000);m.reg_write(UC_ARM_REG_R8,flags);m.reg_write(UC_ARM_REG_R6,0)
   m.reg_write(UC_ARM_REG_R3,0x1a8b5);m.reg_write(UC_ARM_REG_R2,0x1aa19);m.reg_write(UC_ARM_REG_R12,0x12345678)
   m.mem_write(0x2000000+0x1ac,struct.pack('<I',fmt))
   m.hook_add(UC_HOOK_CODE,lambda m,a,s,u:m.emu_stop() if a==bias+0x15030 else None)
   m.emu_start(bias+0x1502c+1,bias+0x90000,count=100)
   expected=(0,0) if fmt in (0xb000000,0xc000000,0xe000000) and flags==1 else (0x1a8b5,0x1aa19)
   assert struct.unpack('<II',m.mem_read(0x2000000+0x50,8))==expected
   assert bool(m.reg_read(UC_ARM_REG_CPSR)&(1<<30))==(r0==0)
   assert m.reg_read(UC_ARM_REG_R12)==0x12345678 and m.reg_read(UC_ARM_REG_SP)==0x1008000
results.append('24 capability cases: software fallback for TrueHD/DTS without HW_AV_SYNC; preserve live CMP flags and registers')

(R/'build/hooks-test.json').write_text(json.dumps({'passed':results,'audio_output_performed':False},indent=2)+'\n');print('\n'.join(results))
