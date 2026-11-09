"""Jiefu supported AudioFlinger property; offline, no device access or other edits."""
from pathlib import Path
import argparse, re
from common import ROOT as R
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--input',type=Path,default=R/'baseline/rootfs/vendor/build.prop')
p.add_argument('--output',type=Path,default=R/'build/vendor.build.prop')
a=p.parse_args()
if a.input.resolve()==a.output.resolve(): raise SystemExit('Use a separate output; keep the original backup')
b=a.input.read_bytes();pattern=rb'(?m)^ro\.af\.client_heap_size_kbyte=([0-9]+)(\r?)$'
match=list(re.finditer(pattern,b))
if len(match)!=1 or match[0].group(1) not in (b'1536',b'8192'):
    raise SystemExit('Expected exactly one Jiefu1536 or already-fixed8192 property')
s=re.sub(pattern,lambda m:b'ro.af.client_heap_size_kbyte=8192'+m.group(2),b)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(s)
print(a.output)
