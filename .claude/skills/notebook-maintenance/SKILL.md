---
name: notebook-maintenance
description: Use when editing wan2gp-google-colab.ipynb or reviewing changes to it — how to safely modify Colab notebook cells, validate the notebook's JSON structure and Python syntax, and update the README changelog per this repo's contributing convention. Trigger on requests to edit the notebook, fix a Colab setup step, change dependency/FFmpeg/PyTorch install logic, or add a new setup cell.
---

# Maintaining the Wan2GP Colab notebook

This repository's only real deliverable is `wan2gp-google-colab.ipynb`, a single
Colab notebook that sets up and launches [Wan2GP](https://github.com/deepbeepmeep/Wan2GP)
on a fresh Colab GPU runtime. There is no app server, test suite, or CI here —
correctness comes from careful editing and manual review, since the notebook's
GPU-dependent cells cannot actually be executed in this environment.

## Notebook structure

15 cells, alternating markdown/code, one setup stage each:

1. Confirm the accelerator (GPU check)
2. Configure workspace path / optional Google Drive persistent storage
3. Download or update Wan2GP (git clone/pull)
4. Install system dependencies (FFmpeg, audio/video libs)
5. Install Python dependencies (reuse Colab's PyTorch, install via `uv`)
5b. Force a headless matplotlib backend
6. Launch Wan2GP (Gradio UI)

Each code cell re-imports everything it needs at the top — treat cells as
independent units, not as one continuous script. Preserve that when editing:
don't assume a variable from an earlier cell is in scope without re-checking,
and don't introduce a cross-cell import dependency that breaks Colab's
top-to-bottom re-run model (users are told to "rerun the notebook from the
top" after a timeout).

## Editing cells

Never hand-edit the raw `.ipynb` JSON with a text editor for anything beyond a
trivial one-line tweak — it's easy to corrupt cell `source` arrays (each line
must keep its own list entry) or the outputs/metadata fields. Instead, edit
with Python's `json` module (load, mutate `cells[i]['source']`, dump), or use
`nbformat` if available. Always dump with `ensure_ascii=False` and keep the
existing indent/newline style so the diff stays minimal.

`source` is a list of strings, one per line, where every line except the last
keeps its trailing `\n`. Match that when writing new cell content.

## Validating a change

Before committing, run the checker script in this skill:

```bash
python3 .claude/skills/notebook-maintenance/scripts/check_notebook.py
```

It confirms the notebook is valid JSON/nbformat and that every code cell's
source parses as valid Python (`ast.parse`), which catches the most common
mistake: a broken edit that leaves a cell with a syntax error that would only
surface when a user actually runs it on Colab. This is a syntax check only —
it cannot exercise GPU install logic, so still reason carefully about runtime
behavior (dependency versions, FFmpeg capability checks, Drive path handling)
by reading the code.

## Updating the README

The README's **Contributing** section asks that notebook changes keep the
README in sync, and the **Changelog** section at the bottom of `README.md`
records dated, user-facing summaries of setup changes (see the existing
`2026-08-07` entry for the expected tone: what changed, why, and any
compatibility note). When a change affects setup behavior, dependency
versions, or install size, add a new dated entry above the existing ones
rather than editing history in place.
