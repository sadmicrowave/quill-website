"""The promo kit's shared pieces: reading a take, drawing the stage, the window chrome, captions, and writing a video.

A *take* is what record_clip.sh saved for one clip: a folder per window with JPEG frames and a times.txt (frame name and host-clock
second), so the windows can be lined up in time. Nothing here knows about a particular clip: clips.py does.
"""
from __future__ import annotations

import bisect
import pathlib
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
TAKES = ROOT / "takes"
OUT = ROOT / "out"
ICON = ROOT.parent / "public" / "assets" / "icon-512.png"
W, H, FPS = 1920, 1080, 30
FONT = "/System/Library/Fonts/Helvetica.ttc"


def font(size: float, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, int(size), index=1 if bold else 0)


clamp = lambda v, a=0.0, b=1.0: max(a, min(b, v))
ease = lambda t: 3 * t * t - 2 * t * t * t
lerp = lambda a, b, t: a + (b - a) * t


# ------------------------------------------------------------------ the take -------------------------------------------------

class Source:
    """One recorded window: its frames in time order."""

    def __init__(self, folder: pathlib.Path):
        rows = [(l.split()[0], float(l.split()[1])) for l in (folder / "times.txt").read_text().splitlines() if l.strip()]
        self.folder, self.files, self.times = folder, [r[0] for r in rows], [r[1] for r in rows]
        self.rel: list[float] = []

    def index(self, g: float) -> int:
        i = min(max(bisect.bisect_left(self.rel, g), 0), len(self.rel) - 1)
        return i - 1 if i > 0 and abs(self.rel[i - 1] - g) < abs(self.rel[i] - g) else i


class Take:
    """All the windows recorded for a clip, on one clock (``g``, seconds since the first frame of any window)."""

    def __init__(self, clip: str):
        self.clip = clip
        base = TAKES / clip
        sources = {p.name: Source(p) for p in sorted(base.iterdir()) if (p / "times.txt").exists()}
        self.sources = {n: s for n, s in sources.items() if s.times}            # (a window that never appeared has no frames)
        t0 = min(s.times[0] for s in self.sources.values())
        for s in self.sources.values():
            s.rel = [t - t0 for t in s.times]
        self.end = max(s.rel[-1] for s in self.sources.values() if s.rel)

    def has(self, name: str, g: float) -> bool:
        s = self.sources.get(name)
        return bool(s and s.rel and s.rel[0] - 0.05 <= g <= s.rel[-1] + 0.05)

    def frame(self, name: str, g: float) -> Image.Image:
        """The window *name* as it was at *g*, with its own title-bar buttons drawn over the screen-capture badge."""
        s = self.sources[name]
        im = Image.open(s.folder / f"{s.files[s.index(g)]}.jpg").convert("RGB")
        return fix_chrome(im, "numbers" if name == "numbers" else "app")

    def start_of_story(self, name: str = "main") -> float:
        """When the scenario began: the first moment the Quill window changed (listening started)."""
        s = self.sources[name]
        crop = (0, 100, min(906, Image.open(s.folder / f"{s.files[0]}.jpg").width), 230)
        base = np.asarray(Image.open(s.folder / f"{s.files[0]}.jpg").convert("L").crop(crop), dtype=float)
        for i in range(20, len(s.files)):
            cur = np.asarray(Image.open(s.folder / f"{s.files[i]}.jpg").convert("L").crop(crop), dtype=float)
            if np.abs(cur - base).mean() > 3:
                return s.rel[i]
        return s.rel[0]

    def window_appeared(self, name: str) -> float | None:
        s = self.sources.get(name)
        return s.rel[0] if s and s.rel else None


# ------------------------------------------------------------------ window chrome --------------------------------------------

#: While a window is being recorded macOS draws a "screen sharing" badge over the red / yellow / green buttons. It is covered with the
#: window's own title-bar colour and the three buttons are drawn again, at the size and place macOS puts them (frame pixels at 2x).
CHROME = {"app": dict(erase=(30, 26, 160, 80), bar=(168, 18)), "numbers": dict(erase=(22, 24, 176, 80), bar=(190, 12))}
LIGHTS = (("#FF5F57", "#E0443E"), ("#FEBC2E", "#DEA123"), ("#28C840", "#1AAB29"))


def fix_chrome(im: Image.Image, kind: str) -> Image.Image:
    spec = CHROME[kind]
    out = im.copy()
    bar = out.getpixel(spec["bar"])
    x0, y0, x1, y1 = spec["erase"]
    ImageDraw.Draw(out).rectangle([x0, y0, x1, y1], fill=bar)
    scale = 4                                                                    # drawn large and reduced: smooth circles
    layer = Image.new("RGBA", (200 * scale, 60 * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, (fill, ring) in enumerate(LIGHTS):
        cx, cy, r = (36 + 40 * i) * scale - 20 * scale, 30 * scale, 12 * scale
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=ring, width=scale)
    layer = layer.resize((200, 60), Image.LANCZOS)
    out.paste(layer, (20, 52 - 30), layer)
    return out


# ------------------------------------------------------------------ the stage ------------------------------------------------

def gradient(w: int, h: int, a=(238, 232, 252), b=(250, 247, 241)) -> Image.Image:
    g = Image.new("RGB", (1, h))
    for y in range(h):
        g.putpixel((0, y), tuple(int(a[i] + (b[i] - a[i]) * y / h) for i in range(3)))
    return g.resize((w, h))


BG = gradient(W, H).convert("RGBA")
_shadows: dict = {}


def sprite(img: Image.Image, w: int, radius: int = 22):
    h = round(img.height * w / img.width)
    im = img.resize((w, h), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    im.putalpha(mask)
    pad = 80
    if (w, h) not in _shadows:
        sh = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 22, pad + w, pad + 22 + h], radius, fill=(40, 24, 90, 95))
        _shadows[(w, h)] = sh.filter(ImageFilter.GaussianBlur(34))
    out = _shadows[(w, h)].copy()
    out.alpha_composite(im, (pad, pad))
    return out, pad


def place(canvas: Image.Image, img: Image.Image, x: float, y: float, w: int, radius: int = 22) -> None:
    """Put *img* (width *w* on stage) at (x, y); a negative y means "centred on the line y = -value"."""
    if y < 0:
        y = -y - round(img.height * w / img.width) / 2
    sp, pad = sprite(img, w, radius)
    canvas.alpha_composite(sp, (int(x - pad), int(y - pad)))


def caption(canvas: Image.Image, text: str, alpha: float) -> None:
    if alpha <= 0.01:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(46, True)
    tw = d.textlength(text, font=f)
    x0, y0 = (W - tw) / 2 - 38, H - 128
    d.rounded_rectangle([x0, y0, x0 + tw + 76, y0 + 82], 41, fill=(52, 31, 115, int(228 * alpha)))
    # "mm" centres the ink of the line, not the font's ascent/descent box, so the text sits in the middle of the pill
    d.text((x0 + 38 + tw / 2, y0 + 41), text, font=f, fill=(255, 255, 255, int(255 * alpha)), anchor="mm")
    canvas.alpha_composite(layer)


def caption_alpha(v: float, start: float, end: float) -> float:
    return clamp((v - start) / 0.3) * clamp((end - v) / 0.3)


def top(im: Image.Image, h: int) -> Image.Image:
    """The top *h* source pixels of a window (zoomed in on the part that shows)."""
    return im.crop((0, 0, im.width, min(h, im.height)))


def card(v: float, title: str | None, line: str, size: int = 112) -> Image.Image:
    """The feather icon with *title* and *line* under it, easing in."""
    f = BG.copy()
    a = clamp(v / 0.6)
    s = int(340 * lerp(0.9, 1.0, ease(clamp(v / 0.9))))
    icon = Image.open(ICON).convert("RGBA").resize((s, s), Image.LANCZOS)
    icon.putalpha(icon.getchannel("A").point(lambda p: int(p * a)))
    f.alpha_composite(icon, ((W - s) // 2, 200 + (340 - s) // 2))
    d = ImageDraw.Draw(f)
    y = 610
    if title:
        ft = font(size, True)
        d.text(((W - d.textlength(title, font=ft)) / 2, y), title, font=ft, fill=(91, 59, 176, int(255 * clamp((v - 0.25) / 0.6))))
        y += size + 40
    fl = font(48)
    d.text(((W - d.textlength(line, font=fl)) / 2, y), line, font=fl, fill=(70, 62, 98, int(255 * clamp((v - 0.5) / 0.6))))
    return f


# ------------------------------------------------------------------ writing video --------------------------------------------

def write_video(path: pathlib.Path, frames, count: int, crf: int = 17) -> None:
    """Encode *count* frames (an iterator of RGB images, 1920x1080) to *path* (H.264, 30 fps)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf), "-preset", "medium",
                          "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)
    for k, frame in enumerate(frames):
        p.stdin.write(frame.convert("RGB").tobytes())
        if k % 90 == 0:
            print(f"  frame {k} / {count}", flush=True)
    p.stdin.close()
    p.wait()
