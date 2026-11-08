"""Render one clip (or a card) to a video:

    python promo/render.py dictate            -> promo/out/dictate.mp4 (1920x1080) and the site's smaller copy
    python promo/render.py all                -> every clip and card
    python promo/render.py stills dictate 3 8 -> PNGs of the clip at those seconds (to look at it)

The site's copies (1280x720, with a poster picture) go to public/assets/clips/.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import imageio_ffmpeg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from clips import CLIPS, FADE, LEAD                                          # noqa: E402
from lib import BG, FPS, OUT, ROOT, Take, caption, caption_alpha, card, clamp, write_video   # noqa: E402
from PIL import Image                                                        # noqa: E402

SITE = ROOT.parent / "public" / "assets" / "clips"
CARDS = {"title": (2.6, lambda v: card(v, "Quill", "Talk to your spreadsheet.")),
         "slogan": (3.6, lambda v: card(v, "Say It. With Quill.", "", size=104))}


def clip_frames(name: str):
    clip, take = CLIPS[name], Take(name)
    s0 = take.start_of_story("main")
    g0 = s0 - LEAD
    length = clip.length or max(take.end - g0 - clip.tail, 2.0)
    count = int(length * FPS)

    def frames():
        for k in range(count):
            v = k / FPS
            f = clip.scene(take, g0 + v)
            for text, a, b in clip.captions:
                caption(f, text, caption_alpha(v, a, b))
            alpha = min(1.0, v / FADE, (length - v) / FADE)
            yield Image.blend(BG, f, clamp(alpha)) if alpha < 1 else f
    return frames(), count, length


def card_frames(name: str):
    length, fn = CARDS[name]
    count = int(length * FPS)

    def frames():
        for k in range(count):
            v = k / FPS
            f = fn(v)
            alpha = min(1.0, v / 0.2, (length - v) / FADE)
            yield Image.blend(BG, f, clamp(alpha)) if alpha < 1 else f
    return frames(), count, length


def site_copy(name: str, path: pathlib.Path) -> None:
    """The clip at 1280x720 for the website, and its poster picture."""
    SITE.mkdir(parents=True, exist_ok=True)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(path), "-vf", "scale=1280:720", "-c:v", "libx264", "-crf", "24", "-preset", "slow",
                    "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(SITE / f"{name}.mp4")], check=True)
    subprocess.run([ff, "-y", "-loglevel", "error", "-ss", "6", "-i", str(path), "-vframes", "1", "-vf", "scale=1280:720", "-q:v", "4",
                    str(SITE / f"{name}.jpg")], check=True)


def render(name: str) -> None:
    frames, count, length = card_frames(name) if name in CARDS else clip_frames(name)
    path = OUT / f"{name}.mp4"
    print(f"{name}: {length:.1f} s")
    write_video(path, frames, count)
    if name in CLIPS:
        site_copy(name, path)


def stills(name: str, seconds: list[float]) -> None:
    clip, take = CLIPS[name], Take(name)
    g0 = take.start_of_story("main") - LEAD
    for v in seconds:
        f = clip.scene(take, g0 + v)
        for text, a, b in clip.captions:
            caption(f, text, caption_alpha(v, a, b))
        OUT.mkdir(exist_ok=True)
        f.convert("RGB").save(OUT / f"still-{name}-{v:05.1f}.png")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "stills":
        stills(args[1], [float(x) for x in args[2:]])
    else:
        for n in (list(CARDS) + list(CLIPS) if args == ["all"] else args):
            render(n)
