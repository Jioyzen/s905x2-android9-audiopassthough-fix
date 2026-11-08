from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[1]
def ndk_bin():
    if os.environ.get("NDK_BIN"):
        result = Path(os.environ["NDK_BIN"]).expanduser().resolve()
    elif os.environ.get("ANDROID_NDK_ROOT"):
        result = Path(os.environ["ANDROID_NDK_ROOT"]).expanduser().resolve()/"toolchains/llvm/prebuilt/linux-x86_64/bin"
    else:
        raise SystemExit("Set ANDROID_NDK_ROOT (NDK r28c) or NDK_BIN first")
    if not (result/"armv7a-linux-androideabi28-clang").is_file():
        raise SystemExit("ARMv7 API28 clang not found in " + str(result))
    return result
