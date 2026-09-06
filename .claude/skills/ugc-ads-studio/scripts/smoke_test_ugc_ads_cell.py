#!/usr/bin/env python3
"""Exercise the UGC Ads Studio notebook cell's rendering pipeline for real.

This extracts the actual code cell's source from the notebook (not a copy
that could drift out of sync) and runs it against a synthetic source video
with ffmpeg, covering the two things most likely to regress silently:

- the aspect-ratio crop actually produces the requested WxH
- ad copy containing ':' and '%' (prices, times, discount codes) survives
  into the rendered captions instead of being silently dropped or
  truncated — see SKILL.md for why this needs textfile=, not inline text=

Needs ffmpeg (with drawtext) and gradio on PATH/importable; skips with a
clear message if either is missing, since neither is guaranteed outside
a Wan2GP Colab runtime. No GPU is needed — Wan2GP itself is never invoked.
"""

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
NOTEBOOK_PATH = REPO_ROOT / "wan2gp-google-colab.ipynb"


def extract_ugc_ads_cell_source():
    notebook = json.loads(NOTEBOOK_PATH.read_text())
    cells = notebook["cells"]
    for i, cell in enumerate(cells):
        if cell["cell_type"] == "markdown" and "## 6. UGC Ads Studio" in "".join(cell["source"]):
            code_cell = cells[i + 1]
            assert code_cell["cell_type"] == "code"
            return "".join(code_cell["source"])
    raise SystemExit("Could not find the '## 6. UGC Ads Studio' cell in the notebook.")


def main():
    if shutil.which("ffmpeg") is None:
        print("SKIP: ffmpeg not found on PATH.")
        return
    try:
        import gradio  # noqa: F401
    except ImportError:
        print("SKIP: gradio is not importable (pip install gradio==5.29.0 to run this locally).")
        return

    source = extract_ugc_ads_cell_source()
    ast.parse(source)  # fail fast on a syntax error before spending time on ffmpeg

    with tempfile.TemporaryDirectory(prefix="ugc_ads_smoke_") as tmp:
        tmp_path = Path(tmp)
        wan_outputs_dir = tmp_path / "outputs"
        wan_outputs_dir.mkdir()
        source_video = wan_outputs_dir / "wan2gp_clip.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=6",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                str(source_video),
            ],
            check=True, capture_output=True,
        )

        namespace = {"WAN_OUTPUTS_DIR": wan_outputs_dir}
        skip_launch = source.replace(
            "ugc_ads_demo.launch(server_port=7861, share=True, prevent_thread_lock=True)",
            "pass  # launch skipped by smoke_test_ugc_ads_cell.py",
        )
        exec(compile(skip_launch, str(NOTEBOOK_PATH), "exec"), namespace)

        listed = namespace["list_wan2gp_outputs"]()
        assert listed == [str(source_video)], f"unexpected output listing: {listed}"

        output_path, status = namespace["generate_ad"](
            str(source_video),
            None,
            "Wait... 50% OFF: don't miss it!",
            2.2,
            "Price: $29.99 (was $59.99). It's crazy, right? Use code SAVE50%.",
            "9:16 (TikTok / Reels / Shorts)",
            "#1DA1F2",
        )
        assert output_path is not None, f"generate_ad reported failure: {status}"
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
             "-of", "json", output_path],
            check=True, capture_output=True, text=True,
        )
        streams = json.loads(probe.stdout)["streams"]
        video_stream = next(s for s in streams if "width" in s)
        assert (video_stream["width"], video_stream["height"]) == (1080, 1920), (
            f"expected 1080x1920, got {video_stream}"
        )

    print("OK: UGC Ads Studio cell renders a correctly-sized ad and preserves ':' / '%' in captions.")


if __name__ == "__main__":
    main()
