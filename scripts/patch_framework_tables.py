"""SN5BBAO PI.4333 only: admit TrueHD without invalidating stripped APK preopt.

The original compact DEX and its AOT native copies contain four shared switch
tables. Only key 14 changes. Keep all code sizes, dex identities, OAT/ART
dependency identities, stack maps, and original framework.jar unchanged.
This is an in-place vendor binary supplement, not a regenerated boot image.
"""
from pathlib import Path
import hashlib,struct,json
from common import ROOT
R=ROOT
O=R/'baseline/rootfs/system/framework'
out=R/'build'
out.mkdir(parents=True,exist_ok=True)
oat=bytearray((O/'arm/boot-framework.oat').read_bytes())
vdex=bytearray((O/'boot-framework.vdex').read_bytes())
assert hashlib.sha256(oat).hexdigest()=='edd48176ecaeb772027894fbee5b7c20cc3e29c878661517dc1fc3b1f14609d1'
assert len(vdex)==20657024
assert hashlib.sha256(vdex).hexdigest()=='3e8cd3d87fedfd419221c7bbe4b1345dae43fd933964fdc5159c0cdb09f68b55'
old_oat=bytes(oat);old_vdex=bytes(vdex);edits=[]
def patch(buf,kind,where,old,new,name):
 assert struct.unpack_from('<I',buf,where)[0]==old,(kind,hex(where))
 struct.pack_into('<I',buf,where,new)
 edits.append({'file':kind,'method':name,'offset':hex(where),'before':old,'after':new,'encoding':14})
# Oatdump offsets are relative to oatdata, whose ELF offset is 0x1000.
# isPublicEncoding and isValidEncoding share both DEX and native code.
for name,base,index,old,new in [
 ('AudioFormat.public/valid',0x80a6fc,12,0x45,0x49),
 ('AudioFormat.isEncodingLinearFrames',0x80a496,13,0x4d,0xe1),
 ('AudioFormat.isEncodingLinearPcm',0x80a5d6,13,0x4d,0xe1),
 ('AudioFormat.Builder.setEncoding',0x7110e6,13,0x67,0x61),
]: patch(oat,'boot-framework.oat',0x1000+base+index*4,old,new,name)
tables=[
 ('AudioFormat.public/valid',2,[5]*12+[3]+[5]*4,5),
 ('AudioFormat.isEncodingLinearPcm',1,[28]*4+[26]*9+[3]+[26]*4,26),
 ('AudioFormat.isEncodingLinearFrames',1,[28]*4+[26]*8+[28,3]+[26]*4,26),
 ('AudioFormat.Builder.setEncoding',1,[29]+[26]*12+[3]+[26]*4,26),
]
for name,first,values,new in tables:
 pattern=struct.pack('<HHI',256,len(values),first)+struct.pack('<'+'i'*len(values),*values)
 start=old_vdex.find(pattern)
 assert start>=0 and old_vdex.find(pattern,start+1)<0,name
 patch(vdex,'boot-framework.vdex',start+8+4*(14-first),3,new,name)
assert sum(a!=b for a,b in zip(oat,old_oat))==4
assert sum(a!=b for a,b in zip(vdex,old_vdex))==4
# Identity headers deliberately remain those of the original optimized image:
# changing identities would invalidate vendor APKs which have no source DEX.
assert oat[:0x2000]==old_oat[:0x2000] and vdex[:0x1000]==old_vdex[:0x1000]
entries=[]
for name,before,after in [('boot-framework.oat',old_oat,oat),('boot-framework.vdex',old_vdex,vdex)]:
 (out/name).write_bytes(after)
 entries.append({'name':name,'source_sha256':hashlib.sha256(before).hexdigest(),'sha256':hashlib.sha256(after).hexdigest(),'changed_bytes':sum(a!=b for a,b in zip(before,after)),'bytes':len(after)})
(out/'framework-table-patch.json').write_text(json.dumps({'files':entries,'edits':edits},indent=2)+'\n')
print(json.dumps(entries,indent=2))
