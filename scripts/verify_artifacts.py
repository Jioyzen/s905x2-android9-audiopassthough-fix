"""Verify archived payload files and pinned dependencies without accessing any device."""
from pathlib import Path
import hashlib,json,sys
from common import ROOT as R
for manifest,key in [('manifests/active-files.json','files'),('manifests/dependencies.json','files')]:
    for f in json.loads((R/manifest).read_text())[key]:
        p=R/f.get('artifact',f.get('path',''))
        assert p.is_file(),p
        assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],p
        print('OK',p.relative_to(R))
