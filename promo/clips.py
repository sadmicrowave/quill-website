"""The clips: what each one shows, how it is laid out on the stage, and its captions.

Each clip is one feature, recorded on its own (record_clip.sh), so a change to one view means re-recording and re-rendering just that
clip, then compiling the promo again (compile.py). Layout numbers are pixels on the 1920 x 1080 stage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from PIL import Image

from lib import BG, H, W, Take, card, clamp, caption, caption_alpha, ease, place, top

LEAD = 1.0                  # seconds shown before the story starts (the window sitting still)
FADE = 0.35                 # seconds a clip fades in from, and out to, the stage


@dataclass
class Clip:
    name: str
    scene: Callable[[Take, float], Image.Image]          # (take, g) -> the stage with the windows on it
    captions: list = field(default_factory=list)          # (text, from, to), seconds into the clip
    length: float = 0.0                                   # seconds; 0 = to the end of what was recorded
    tail: float = 0.0                                     # seconds trimmed off the end of the recording


def crop_numbers(im: Image.Image, h: int = 900) -> Image.Image:
    """The spreadsheet window without its inspector panel on the right."""
    return im.crop((0, 0, 1810, min(h, im.height)))


def detail_pair(take: Take, f: Image.Image, g: float, helper: str = "helper") -> None:
    """The Term Helper and the main window at the SAME zoom (one scale for both), side by side."""
    s, gap = 0.95, 40
    hs, ms = take.frame(helper, g), top(take.frame("main", g), 840)
    hw, mw = round(hs.width * s), round(ms.width * s)
    x = (W - hw - mw - gap) / 2
    place(f, hs, x, -500, hw)
    place(f, ms, x + hw + gap, -500, mw)


# ---------------------------------------------------------------- scenes ------------------------------------------------------

def scene_dictate(take: Take, g: float) -> Image.Image:
    """The spreadsheet, with the Quill window large and laid over its right-hand side."""
    f = BG.copy()
    place(f, crop_numbers(take.frame("numbers", g)), 40, -500, 1270)
    place(f, top(take.frame("main", g), 840), 1000, -520, 700)
    return f


def scene_helper(take: Take, g: float) -> Image.Image:
    f = BG.copy()
    if take.has("helper", g):
        detail_pair(take, f, g)
    else:
        main = top(take.frame("main", g), 840)
        place(f, main, (W - main.width) / 2, -500, main.width)
    return f


def scene_learns(take: Take, g: float) -> Image.Image:
    f = BG.copy()
    if take.has("settings", g):
        place(f, take.frame("settings", g), (W - 940) // 2, -500, 940)
    elif take.has("helper", g):
        detail_pair(take, f, g)
    else:
        main = top(take.frame("main", g), 840)
        place(f, main, (W - main.width) / 2, -500, main.width)
    return f


_MINI_HEIGHT: dict[str, int] = {}


def _mini_height(take: Take, sample: Image.Image) -> int:
    """The mini window's real height in the recording: below it the frame is pure white (the window shrank after the recording began)."""
    if take.clip not in _MINI_HEIGHT:
        sample = take.frame("main", take.start_of_story("main") + 5)         # (once the window has shrunk)
        y = sample.height - 1
        while y > 0 and sample.getpixel((20, y)) == (255, 255, 255):
            y -= 1
        _MINI_HEIGHT[take.clip] = y + 4
    return _MINI_HEIGHT[take.clip]


def scene_mini(take: Take, g: float) -> Image.Image:
    """The mini view in proportion: a slim strip laid over the corner of a normal spreadsheet window."""
    f = BG.copy()
    sheet_w = 1500
    place(f, crop_numbers(take.frame("numbers", g), 1000), 120, -520, sheet_w)
    mini = take.frame("main", g)
    mini = mini.crop((0, 0, mini.width, _mini_height(take, mini)))      # (the recording was started at the full window's height)
    points_per_px = 1180 / 2360                                         # the spreadsheet window is 1180 pt wide, recorded at 2x
    stage_per_point = sheet_w / (1810 * points_per_px)                  # (the sheet is shown without its inspector: 1810 of 2360 px)
    mw = round(mini.width * points_per_px * stage_per_point)            # Quill's mini view is about 470 pt wide
    place(f, mini, 120 + sheet_w - mw - 50, 330, mw, radius=16)
    return f


CLIPS = {
    "dictate": Clip("dictate", scene_dictate, [("Press Start. Just talk.", 1.4, 4.6), ("Quill hears values, not just words.", 5.0, 8.6),
                                               ("Each row lands in your spreadsheet, live.", 9.0, 14.6)]),
    "helper": Clip("helper", scene_helper, [("Say a row, even with words it hasn't met.", 1.2, 5.0), ("Unknown words go to the Term Helper.", 5.4, 9.2),
                                            ("Answer by voice: “color… yes… ignore”.", 9.6, 16.0)], length=17.5),
    "learns": Clip("learns", scene_learns, [("Slurred words sneak in: “kinda cream”.", 2.0, 6.0), ("Trim what isn't part of the value…", 6.6, 10.0),
                                            ("…and Quill skips it from now on.", 10.4, 14.0), ("Teach it your words: “sold means sale date”.", 15.0, 19.0),
                                            ("Everything it learns is listed in Settings.", 20.5, 24.5),
                                            ("Learned Words, and Words To Skip: yours to edit.", 25.0, 29.5)], length=30.5),
    "mini": Clip("mini", scene_mini, [("Mini view: a slim strip beside your spreadsheet.", 1.6, 6.0), ("Start or Stop, the Term Helper count, Next Row.", 6.4, 11.0),
                                      ("Small enough to sit right over your spreadsheet.", 11.4, 15.0)]),
}
