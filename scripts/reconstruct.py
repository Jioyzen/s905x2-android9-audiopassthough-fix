"""Reconstruct exact archived files from matching original rootfs; offline, no device writes."""
from pathlib import Path
import base64, hashlib, json, zlib
from common import ROOT as R
M=json.loads((R/'manifests/active-files.json').read_text())
for item in M['files']:
    target=item['target']; orig=R/'baseline/rootfs'/target.lstrip('/')
    if hashlib.sha256(orig.read_bytes()).hexdigest()!=item['source_sha256']:
        raise SystemExit('Original SHA mismatch: '+target)
    patch=R/'patches'/(Path(target).name+'.json')
    if patch.exists():
        data=bytearray(orig.read_bytes()); meta=json.loads(patch.read_text())
        if len(data)>meta['size']: del data[meta['size']:]
        else: data.extend(b'\0'*(meta['size']-len(data)))
        for part in meta['ranges']:
            at=part['offset']; before=bytes.fromhex(part['before'])
            assert data[at:at+len(before)]==before
            payload=zlib.decompress(base64.b64decode(part['after']))
            data[at:at+len(payload)]=payload
    else:
        # The SPDIF library is rebuilt from source; the exact verified link is archived too.
        data=(R/item['artifact']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==item['sha256'],target
    output=R/'build/reconstructed/rootfs'/target.lstrip('/');output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
    print('OK',target)
