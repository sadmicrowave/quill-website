"""Compile the promo from the clip videos in promo/out/: title card, the clips in order, the slogan card.

    python promo/compile.py                  -> promo/out/promo.mp4, copied to public/assets/promo.mp4 (with its poster)

Every clip fades in from and out to the stage, so they are simply joined. Re-record a clip, re-render just it, run this again.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import imageio_ffmpeg

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import OUT                                                       # noqa: E402

ORDER = ["title", "dictate", "helper", "learns", "mini", "slogan"]
SITE_ASSETS = HERE.parent / "public" / "assets"

missing = [n for n in ORDER if not (OUT / f"{n}.mp4").exists()]
if missing:
    sys.exit(f"render these first: {', '.join(missing)}  (python promo/render.py {' '.join(missing)})")
ff = imageio_ffmpeg.get_ffmpeg_exe()
listing = OUT / "promo-list.txt"
listing.write_text("".join(f"file '{OUT / (n + '.mp4')}'\n" for n in ORDER))
promo = OUT / "promo.mp4"
subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(promo)], check=True)
shutil.copy(promo, SITE_ASSETS / "promo.mp4")
subprocess.run([ff, "-y", "-loglevel", "error", "-ss", "8", "-i", str(promo), "-vframes", "1", "-vf", "scale=1600:-1", "-q:v", "3", str(SITE_ASSETS / "poster.jpg")], check=True)
print("promo:", promo, f"({promo.stat().st_size // 1024} KB), copied to public/assets/")
