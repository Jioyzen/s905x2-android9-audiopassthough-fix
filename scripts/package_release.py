from pathlib import Path
import hashlib,json,tarfile
from common import ROOT as R
version=json.loads((R/'manifests/active-files.json').read_text())['version']
out=R/'dist';out.mkdir(exist_ok=True);archive=out/f'jiefu-audio-{version}.tar.xz'
with tarfile.open(archive,'w:xz') as tar:
    for p in sorted((R/'artifacts').rglob('*')):
        if p.is_file(): tar.add(p,arcname=str(p.relative_to(R/'artifacts')),recursive=False)
    for src,dest in [('manifests/active-files.json','active-files.json'),('docs/部署与回退.md','部署与回退.md'),('README.md','README.md'),('NOTICE.md','NOTICE.md')]:tar.add(R/src,arcname=dest)
(out/'SHA256SUMS').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print(archive)
