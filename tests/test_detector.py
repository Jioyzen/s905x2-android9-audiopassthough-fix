from pathlib import Path
import sys,struct,json
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_hal_hooks import machine,symbols,bias
from elftools.elf.elffile import ELFFile
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[1]
with (R/'build/hooks.elf').open('rb') as f:
 local_symbols={s.name:s['st_value']&~1 for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols()}
SLOT=0x2000100;DATA=0x2002000;STOP=bias+0x8ff00

def run_call(m,sym,args):
 for reg,val in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2],args):m.reg_write(reg,val)
 m.reg_write(UC_ARM_REG_LR,STOP+1);m.emu_start(bias+symbols[sym]+1,bias+0x90000,count=3000000)
 assert m.reg_read(UC_ARM_REG_PC)==STOP and m.reg_read(UC_ARM_REG_SP)==0x1008000
 return m.reg_read(UC_ARM_REG_R0)

def detector(payload,chunk):
 m=machine();m.mem_write(SLOT-1,b'\xa5\0\0\0\x5a');m.hook_add(UC_HOOK_CODE,lambda m,a,s,u:m.emu_stop() if a==STOP else None)
 found=[]
 for i in range(0,len(payload),chunk):
  p=payload[i:i+chunk];m.mem_write(DATA,p)
  if run_call(m,'jf_dts_boundary',[SLOT,DATA,len(p)]):found.append(i+len(p))
  assert bytes(m.mem_read(SLOT-1,1))==b'\xa5' and bytes(m.mem_read(SLOT+3,1))==b'\x5a'
 return found
results=[]
for name,hd in [('dts.dts',False),('dts-full.dts',False),('dtshd.dts',True)]:
 data=(R/'fixtures'/name).read_bytes()
 for chunk in [1,7,2052,4096]:
  found=detector(data,chunk);assert bool(found)==hd,(name,chunk,found)
  results.append({'fixture':name,'chunk':chunk,'hd_detected':bool(found)})
# False EXSS inside the compressed core must never promote a stream.
core=bytearray((R/'fixtures/dts-full.dts').read_bytes()[:2048]);core[24:28]=b'\x64\x58\x20\x25'
for chunk in [1,7,2052]:assert not detector(bytes(core)*3,chunk)
# All split positions around core header/boundary; leading junk/partial sync.
hd=(R/'fixtures/dtshd.dts').read_bytes()
for prefix in [b'\x7f',b'garbage\x7f\xfe',b'\x64\x58\x20\x25']:
 assert detector(prefix+hd,7)
results.append({'negative':'core payload EXSS is ignored; leading noise and fragmented sync recover'})
# Real ARM prepare helper: promotes only supported plain 48k DTS with EXSS.
for supported,fmt,rate,flags,standby in [(s,fmt,rate,flags,st) for s in [0,1] for fmt,rate,flags in [(0xb000000,48000,1),(0xb000000,48000,0x41),(0xb000000,48000,0x401),(0xb000000,96000,1),(0x9000000,48000,1),(0xe000000,48000,1)] for st in [0,1]]:
 m=machine();stream=0x2000000;m.mem_write(DATA,hd)
 for off,val in [(0xf4,fmt),(0xf8,rate),(0xfc,flags),(0x1ac,fmt),(0xcc,rate),(0x108,0x12345678)]:m.mem_write(stream+off,struct.pack('<I',val))
 m.mem_write(stream+0x118,bytes([standby]));m.mem_write(stream+0x130,struct.pack('<Q',123456789))
 calls=[]
 def mock(m,a,s,u):
  if a==STOP:m.emu_stop()
  elif a in [bias+symbols['jf_hd_supported'],bias+local_symbols['sink_channels']]:
   assert m.reg_read(UC_ARM_REG_R0)==0xc000000;m.reg_write(UC_ARM_REG_R0,supported);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  elif a==bias+0x1b8e4:
   calls.append('internal_standby');assert m.reg_read(UC_ARM_REG_R0)==stream
   m.mem_write(stream+0x118,b'\1');m.mem_write(stream+0x108,b'\0'*4);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
 m.hook_add(UC_HOOK_CODE,mock);run_call(m,'jf_dts_prepare',[stream,DATA,len(hd)])
 promote=bool(supported and fmt==0xb000000 and rate==48000 and flags==1)
 assert struct.unpack('<I',m.mem_read(stream+0x1ac,4))[0]==(0xc000000 if promote else fmt)
 assert struct.unpack('<I',m.mem_read(stream+0xcc,4))[0]==(192000 if promote else rate)
 assert calls==(['internal_standby'] if promote and not standby else [])
 assert struct.unpack('<Q',m.mem_read(stream+0x130,8))[0]==123456789
 assert struct.unpack('<I',m.mem_read(stream+0xf4,4))[0]==fmt
results.append({'prepare':'24 ARM cases: EDID denied, tunnel/IEC prepacked, 96k and other codecs untouched; public format and 64-bit frame baseline preserved'})
# DTS-ES 6.1 must keep the ordinary core carrier and original encoding.
for mask in [0x3f,0x13f,0x63f]:
 for fixture in ['dts.dts','dts-full.dts']:
  m=machine();stream=0x2000000;payload=(R/'fixtures'/fixture).read_bytes();m.mem_write(DATA,payload)
  for off,val in [(0xf0,mask),(0xf4,0xb000000),(0xf8,48000),(0xfc,1),(0x1ac,0xb000000),(0xcc,48000)]:m.mem_write(stream+off,struct.pack('<I',val))
  def core_only(m,a,s,u):
   if a==STOP:m.emu_stop()
   elif a in [bias+symbols['jf_hd_supported'],bias+local_symbols['sink_channels'],bias+0x1b8e4]:raise AssertionError('core DTS must not query HD/standby/promote')
  m.hook_add(UC_HOOK_CODE,core_only);run_call(m,'jf_dts_prepare',[stream,DATA,len(payload)])
  assert struct.unpack('<I',m.mem_read(stream+0x1ac,4))[0]==0xb000000
  assert struct.unpack('<I',m.mem_read(stream+0xcc,4))[0]==48000
  assert struct.unpack('<I',m.mem_read(stream+0xf0,4))[0]==mask
results.append({'DTS_ES_core':'6 mask/payload combinations including 0x13f remain native DTS/48k, without HD promotion or standby; synthetic layout coverage, not a real DTS-ES listening test'})

# The actual installed write trampoline passes raw buffer and keeps stack ABI.
m=machine();stream=0x2000000;m.reg_write(UC_ARM_REG_R9,stream);m.reg_write(UC_ARM_REG_R10,DATA);m.reg_write(UC_ARM_REG_R5,2052)
m.mem_write(stream+0x118,b'\1');m.mem_write(stream+0x1ac,struct.pack('<I',0xb000000));m.reg_write(UC_ARM_REG_R1,0xabcdef01)
def trampoline(m,a,s,u):
 if a==bias+symbols['jf_dts_prepare']:
  assert [m.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]==[stream,DATA,2052]
  m.mem_write(stream+0x1ac,struct.pack('<I',0xc000000));m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
 elif a==bias+0x18a98:m.emu_stop()
m.hook_add(UC_HOOK_CODE,trampoline);m.emu_start(bias+0x18a94+1,bias+0x90000,count=1000)
assert m.reg_read(UC_ARM_REG_R0)==1 and m.reg_read(UC_ARM_REG_R1)==0xabcdef01
assert m.reg_read(UC_ARM_REG_SP)==0x1008000 and struct.unpack('<I',m.mem_read(0x1008000+0x54,4))[0]==0xc000000
results.append({'trampoline':'write arguments, original standby load, live internal-format stack snapshot and stack/register preservation verified'})
(R/'build/detector-tests.json').write_text(json.dumps({'passed':results,'audio_output_performed':False},indent=2)+'\n')
print('DTS boundary and HAL integration tests passed:',len(results))
