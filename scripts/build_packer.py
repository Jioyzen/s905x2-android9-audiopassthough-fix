from pathlib import Path
import subprocess, tarfile
from common import ROOT as R, ndk_bin
T=ndk_bin(); src=R/'src/spdif'; frozen=R/'third_party/ffmpeg-armv7'; out=R/'build'; out.mkdir(exist_ok=True)
source=out/'ffmpeg-source'
if not source.exists():
    source.mkdir()
    with tarfile.open(R/'third_party/FFmpeg-n8.1.3-source.tar.xz') as tar:
        tar.extractall(source, filter='data')
# The archived git tree is normally rooted at libavformat/, not a release directory.
headers=source if (source/'libavformat/avformat.h').exists() else next(p.parent.parent for p in source.glob('*/libavformat/avformat.h'))
def run(args): subprocess.run([str(a) for a in args],check=True)
run([T/'armv7a-linux-androideabi28-clang','-ffile-prefix-map='+str(src)+'=android-audio/reference/android12-fix/src/spdif','-O2','-fPIC','-I'+str(frozen),'-I'+str(headers),'-I'+str(src/'include'),'-c',src/'ffmpeg_hdpack.c','-o',out/'ffmpeg_hdpack.o'])
run([T/'armv7a-linux-androideabi28-clang++','-ffile-prefix-map='+str(src)+'=android-audio/reference/android12-fix/src/spdif','-fPIC','-O2','-nostdlib++','-fno-exceptions','-fno-rtti','-fvisibility=default','-w','-I'+str(R/'src/include'),'-I'+str(src/'include'),'-I'+str(src),'-shared','-Wl,-soname,libdroidaudiospdif.so','-Wl,--gc-sections','-Wl,--no-undefined','-L'+str(R/'third_party/link-stubs'),'-o',out/'libdroidaudiospdif.so',*[src/n for n in ['SPDIFEncoderHD.cpp','AC3FrameScanner.cpp','DTSFrameScanner.cpp','FrameScanner.cpp','BitFieldParser.cpp','abi_alias.S']],out/'ffmpeg_hdpack.o','-Wl,--start-group',*[frozen/n for n in ['libavformat.a','libavcodec.a','libavutil.a']],'-Wl,--end-group','-lc++','-llog','-lm'])
run([T/'llvm-strip','--strip-unneeded',out/'libdroidaudiospdif.so'])
