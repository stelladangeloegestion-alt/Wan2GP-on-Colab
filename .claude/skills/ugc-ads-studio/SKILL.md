---
name: ugc-ads-studio
description: Use when editing the "UGC Ads Studio" section of wan2gp-google-colab.ipynb (the Gradio app that turns a Wan2GP clip into a hook + captioned + aspect-ratio-cropped ad) or its smoke test — changing caption styling/timing, aspect ratios, the drawtext filtergraph, or the outputs-list/upload wiring. Trigger on requests to change the UGC ad generator, its hook/caption rendering, or fix a drawtext/ffmpeg escaping issue in that cell.
---

# Maintaining UGC Ads Studio

`wan2gp-google-colab.ipynb` has a section titled **"6. UGC Ads Studio"** (a
markdown cell followed by one code cell) that launches its own Gradio app,
independent of Wan2GP's, on port `7861` with `prevent_thread_lock=True` so
the notebook keeps running into the final "Launch Wan2GP" cell. It takes a
clip Wan2GP already generated (or an uploaded video), and produces a
publish-ready UGC-style ad: a bold hook overlay for the first few seconds,
burned-in captions timed across the rest of the script, cropped to the
aspect ratio the user picks (9:16 / 4:5 / 1:1 / 16:9). Outputs go to
`outputs/ugc_ads`, alongside Wan2GP's own outputs.

Read `.claude/skills/notebook-maintenance/SKILL.md` first for the general
rules on editing this notebook (edit via Python's `json` module, never
hand-edit the raw JSON; cells are independent, re-import everything they
need; run the notebook checker before committing). This skill only adds
what's specific to the UGC Ads Studio cell.

## The one thing not to "simplify" away

Caption and hook text are written to temporary `.txt` files and passed to
ffmpeg's `drawtext` filter via `textfile=<path>:expansion=none`, **not**
inlined as `text='...'` in the `filter_complex` string. This looks like
unnecessary indirection, but it is load-bearing: verified empirically
against a real ffmpeg build (Ubuntu 24.04's packaged ffmpeg, and separately
against the BtbN GPL build this same notebook installs in step 4) that:

- The filtergraph parser terminates a `drawtext` `text=` value at the first
  **unescaped `:`**, regardless of backslash-escaping (`\:`) or wrapping the
  whole value in `'...'` single quotes — both of which the ffmpeg docs
  describe as sufficient, and neither of which worked in practice. Ad copy
  almost always contains a colon (prices with times, "Buy 1: Get 1", ratios),
  so this silently truncates the caption to whatever came before it and
  resets `fontsize`/`x`/`y` to drawtext's defaults (tiny text at the
  top-left) instead of erroring.
- drawtext's own `%`-expansion (for `%{...}` directives, on by default)
  aborts the entire draw call with a "Stray %" warning on an unescaped `%`
  in the text — and discount codes/percentages are exactly the kind of copy
  this tool exists to caption.

Routing text through files sidesteps both: the filtergraph string never
contains the ad copy, so colons in it can't confuse the outer parser, and
`expansion=none` on the `drawtext` call disables `%`-expansion entirely so
a literal `%` in the file just renders as `%`. If you ever refactor this
back to inline `text=`, you will reintroduce this bug — the smoke test below
will catch it, but understanding why it's built this way should stop you
from trying.

## Testing a change

GPU-dependent parts of this notebook can't run outside Colab, but this
cell's rendering pipeline is pure ffmpeg + Gradio wiring and needs neither a
GPU nor Wan2GP itself. Use the smoke test in this skill:

```bash
python3 .claude/skills/ugc-ads-studio/scripts/smoke_test_ugc_ads_cell.py
```

It extracts the actual code cell's source straight from the notebook (so it
can't drift out of sync with a copy), execs it against a synthetic ffmpeg
`testsrc` clip with `launch()` skipped, and asserts: the output lists the
synthetic clip, `generate_ad` succeeds on ad copy containing `:` and `%`,
and the rendered file is actually cropped to the requested aspect ratio
(1080x1920 for the 9:16 preset). It needs `ffmpeg` and `gradio==5.29.0` (the
version this notebook's step 5 installs from Wan2GP's `requirements.txt`) —
it prints `SKIP: ...` and exits cleanly if either is missing rather than
failing, since neither is guaranteed present outside a Wan2GP Colab runtime.

After any change, also run the general notebook checker:

```bash
python3 .claude/skills/notebook-maintenance/scripts/check_notebook.py
```

## Things that are easy to get wrong here

- **Font path**: `find_bold_font()` only checks DejaVu and Liberation Bold
  paths, then apt-installs `fonts-dejavu-core` as a fallback. If you add a
  style option that needs a different weight/family, extend the candidate
  list and the apt-get fallback together — don't assume the font is present.
- **Port**: Wan2GP's own launch cell binds `7860`. This cell must keep using
  a different port (`7861`) so both Gradio apps can run at once; don't let
  the two collide if you copy launch options between them.
- **`gr.Video` upload value**: the callback can receive a plain path string
  or an object exposing `.name`/`.path` depending on Gradio version/source
  type; `generate_ad` normalizes this defensively — keep that if you touch
  the upload wiring, rather than assuming a bare string.
- **Caption pacing**: `WORDS_PER_SECOND` / `MIN_CHUNK_SECONDS` /
  `MAX_WORDS_PER_CHUNK` control how the script is split into caption chunks
  and how long each stays on screen; timings are spread evenly across
  `(video_duration - hook_duration)`, not fixed-duration, so a change to one
  constant changes pacing for every clip length, not just the test case.
