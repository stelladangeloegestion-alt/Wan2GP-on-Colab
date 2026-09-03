#!/usr/bin/env python3
"""Validate wan2gp-google-colab.ipynb: valid nbformat JSON, and every code
cell parses as syntactically valid Python.

Usage: python3 check_notebook.py [path/to/notebook.ipynb]
"""

import ast
import json
import sys
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[4] / "wan2gp-google-colab.ipynb"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH

    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: {path} is not valid JSON: {exc}")
        return 1

    if notebook.get("nbformat") != 4:
        print(f"FAIL: unexpected nbformat {notebook.get('nbformat')!r}, expected 4")
        return 1

    cells = notebook.get("cells", [])
    if not cells:
        print("FAIL: notebook has no cells")
        return 1

    errors = []
    code_cell_count = 0
    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        code_cell_count += 1
        source = "".join(cell.get("source", []))
        try:
            ast.parse(source)
        except SyntaxError as exc:
            errors.append(f"  cell {index}: {exc.__class__.__name__}: {exc}")

    if errors:
        print(f"FAIL: {len(errors)} code cell(s) have syntax errors:")
        print("\n".join(errors))
        return 1

    print(
        f"OK: {path.name} is valid nbformat 4 JSON with "
        f"{len(cells)} cells ({code_cell_count} code cells), all parse cleanly."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
