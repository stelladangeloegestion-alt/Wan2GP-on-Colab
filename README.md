# Wan2GP on Google Colab

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Square-Zero-Labs/Wan2GP-on-Colab/blob/main/wan2gp-google-colab.ipynb)

## Video walkthrough

[![Wan2GP on Colab video walkthrough](https://img.youtube.com/vi/kpKYu1TaarI/hqdefault.jpg)](https://youtu.be/kpKYu1TaarI "Watch the Wan2GP Colab setup walkthrough")

## Overview

This repository provides a single Google Colab notebook that automates setting up the [Wan2GP](https://github.com/deepbeepmeep/Wan2GP) AI video generation platform in a fresh GPU-backed Colab runtime.

**Warning:** free Colab GPU runtimes usually provide only 15 GB of T4 VRAM, which is too small for most Wan2GP checkpoints; stick to the `Wan 2.2 TextImage2Video 5B FastWan` model and select 480p to run without memory errors.

Run the notebook top to bottom to clone Wan2GP, install all system and Python dependencies, and launch the Gradio interface from Colab.

## Notebook workflow

1. **Confirm GPU runtime** – prompts you to enable a GPU accelerator before continuing.
2. **Configure the workspace path and optional persistent data storage** – Wan2GP itself runs from fast ephemeral storage in `/content`; set `USE_GOOGLE_DRIVE_DATA = True` only if you want Google Drive to keep checkpoints, LoRAs, outputs and model caches across Colab restarts.
3. **Download or update Wan2GP** – clones the upstream repository into `/content/Wan2GP` or pulls the latest changes when it already exists, then links Wan2GP's checkpoint and output folders into the selected data root.
4. **Install system dependencies** – installs video and audio libraries required by Wan2GP, verifies FFmpeg's required capabilities, and installs an integrity-checked stable FFmpeg build if Colab's copy is too old.
5. **Install Python dependencies** – reuses the PyTorch build already present in the Colab runtime when it is suitable, and installs Wan2GP's requirements.
6. **UGC Ads Studio** – launches a second, independent Gradio app (its own public link) that turns a clip Wan2GP just generated into a publish-ready UGC-style ad: a bold hook for the first couple of seconds, burned-in captions for the rest of the script, and a crop to your ad platform's aspect ratio (9:16, 4:5, 1:1, or 16:9). Outputs are saved to `outputs/ugc_ads`.
7. **Launch Wan2GP** – starts the Gradio UI; keep the cell running while you interact with Wan2GP.

## Requirements

- Google account with access to Colab GPU runtimes (free tier works; paid tiers provide more VRAM).
- Stable internet connection while the setup cells run (downloads the Wan2GP repository and model weights).

## Tips

- Colab may time out inactive sessions; rerun the notebook from the top to rehydrate the environment.
- Keep the final cell running to maintain the public Gradio link; stopping it will terminate the interface.

## Contributing

Issues and pull requests are welcome. If you notice changes in Colab runtimes or Wan2GP dependencies, please open a PR so the notebook stays up to date.

## Changelog

### 2026-09-06 — UGC Ads Studio

Added a new notebook step that turns a Wan2GP-generated clip into a publish-ready UGC-style ad: a bold hook overlay for the first couple of seconds, burned-in captions timed to the rest of your script, and a crop to the aspect ratio your ad platform wants (9:16, 4:5, 1:1, or 16:9). It runs as its own Gradio app on a separate public link, so it stays usable alongside Wan2GP's own UI. Outputs are saved to `outputs/ugc_ads`, so they persist to Google Drive too when persistent storage is enabled. Captions are rendered via on-disk `textfile=` inputs to ffmpeg's `drawtext` filter rather than inlined text, which avoids Colab's ffmpeg build mis-parsing ad copy containing colons or `%` (prices, times, discount codes).

### 2026-08-07 — faster, more reliable setup

Setup downloads roughly 4 GB less. No models were dropped — Wan2GP's `requirements.txt` is installed unchanged. Tested on a free-tier Colab T4.

- Reuse the runtime's existing PyTorch instead of force-reinstalling 2.8.0, which re-downloaded every CUDA wheel Colab already had.
- Install requirements with [uv](https://github.com/astral-sh/uv) rather than pip, for much faster dependency resolution.
- Drop `xformers`: Wan2GP never picks it on a T4, and it was the only reason PyTorch was pinned to 2.8.0.
- Install an ONNX Runtime build matching Colab's CUDA version, with an automatic CPU fallback so Wan2GP always starts.
- Fix Wan2GP updates being silently skipped after the first run.
- Skip `apt-get` when the libraries are already present, and cache downloaded packages on Drive when Drive storage is enabled.
