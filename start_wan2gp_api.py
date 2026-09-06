"""Start the authenticated Wan2GP API inside an already prepared Colab runtime."""
from __future__ import annotations

import os
import secrets
import subprocess
import sys

api_key = os.environ.get("WAN2GP_API_KEY")
if not api_key:
    api_key = secrets.token_urlsafe(32)
    os.environ["WAN2GP_API_KEY"] = api_key
    print("WAN2GP_API_KEY was not set, so a temporary key was generated for this Colab session:")
    print(api_key)
    print("Keep this value private. It stops when the Colab runtime stops.")

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "fastapi", "uvicorn"],
    check=True,
)

port = os.environ.get("WAN2GP_API_PORT", "7861")
print(f"Starting Wan2GP API on port {port}...")
os.execv(
    sys.executable,
    [sys.executable, "-m", "uvicorn", "wan2gp_api:app", "--host", "0.0.0.0", "--port", port],
)
