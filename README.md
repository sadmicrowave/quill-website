# Quill website

The front-facing landing page and download page for [Quill](https://github.com/sadmicrowave/quill-dictation-app), deployed on Vercel.

* One scrollable landing page (`public/index.html`): fixed nav, a full-width promo video that plays by itself with a **Download now** button in its top corner, feature sections whose vector screenshots ease in from the page margins as they scroll into view, and a full-width download segment at the bottom.
* `public/download.html`: the Mac and Windows downloads with install steps.
* **Styling: Tailwind CSS v4** (`src/input.css`, built to `public/assets/site.css`, which is not committed).
* The download buttons read the newest GitHub release of `sadmicrowave/quill-dictation-app` in the browser (`public/js/main.js`), so a new Quill release never needs a site rebuild. Before the first release they say "Release coming soon".

## Work on it

```bash
npm install
npm run build        # builds public/assets/site.css
npm run preview      # serves public/ on a local port
npm run dev          # rebuild the CSS on every change (run in a second terminal)
```

## The vector screenshots

`public/assets/screens/*.svg` are the **real Quill windows** drawn offscreen as vector PDFs and converted to SVG with the text as outlines, so they stay sharp at any size and need no font. After the app's look changes:

```bash
pip install pymupdf
npm run screens      # ../quill-dictation-app/.venv/bin/python tools/make_pdfs.py && python3 tools/pdf_to_svg.py
```

(`tools/make_pdfs.py` draws the windows with the app's own code, so it needs the sibling `quill-dictation-app` checkout and its virtualenv.)

## The video

`public/assets/promo.mp4` (and its `poster.jpg`) are the 60-second promo recorded from the live app (see `../Promo Video/`). Replace the files to change the hero.

## Deploy

Import the repository in Vercel. `vercel.json` sets the build (`npm run build`) and the output folder (`public`). No environment variables are needed.
