# The promo kit

The site's promo video and its feature videos are made from **clips**: one short, self-contained recording of the real Quill app per
feature. When a view changes, record and render just that clip, then compile the promo again. The same clips play on repeat on the
landing page.

| clip | shows | recorded windows |
|---|---|---|
| `dictate` | rows spoken and saved into the open spreadsheet (Numbers) | Numbers, Quill |
| `helper` | the Term Helper answered by voice | Quill, Term Helper |
| `learns` | a word trimmed off a term, a word taught by voice, Settings > Learned Words | Quill, Term Helper, Settings |
| `mini` | the mini view beside the spreadsheet | Numbers, Quill (mini) |

The scenarios live in the app (`quill-dictation-app/quill/demo.py`: *Clip: …*); the demo uses its own throw-away settings, so nothing
you taught your real Quill is touched, and the sample sheet has no drop-down arrows (the recorder formats it as plain cells).

## Make or refresh a clip

```bash
promo/tools/build.sh                         # once: builds the window recorder (ScreenCaptureKit)
python3 -m venv .venv && .venv/bin/pip install -r promo/requirements.txt     # once: Pillow, numpy, ffmpeg

promo/record_clip.sh helper                  # records the live app into promo/takes/helper/ (about two minutes)
.venv/bin/python promo/render.py stills helper 4 9 14      # look at a few moments: promo/out/still-helper-*.png
.venv/bin/python promo/render.py helper      # promo/out/helper.mp4 (1920x1080) and the site's copy in public/assets/clips/
.venv/bin/python promo/compile.py            # joins title + clips + slogan: promo/out/promo.mp4, copied to public/assets/promo.mp4
```

Needs the built app (`quill-dictation-app/dist/Quill.app`, from `tools/build_mac.sh`), macOS 12.3+ and the Screen Recording permission for
your terminal. The Numbers clips need Numbers.

## What is in the folders

* `lib.py` the take reader (lines the windows up by the host clock), the stage, captions, and the **window chrome fix**: while a window is
  recorded macOS draws a "sharing" badge over its red / yellow / green buttons, so the badge is covered and the three buttons are drawn
  again, where macOS puts them.
* `clips.py` each clip's layout, captions and timing. Change a caption or a position here and re-render that clip.
* `render.py`, `compile.py` as above. `takes/` (raw frames, large) and `out/` are not committed.
