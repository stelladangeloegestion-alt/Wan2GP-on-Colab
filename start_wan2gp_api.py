"""Start the Wan2GP API and an authenticated public Cloudflare Quick Tunnel in Colab."""
from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

api_key = os.environ.get("WAN2GP_API_KEY")
if not api_key:
    api_key = secrets.token_urlsafe(32)
    os.environ["WAN2GP_API_KEY"] = api_key
    print("WAN2GP_API_KEY (keep private):")
    print(api_key)

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "fastapi", "uvicorn"],
    check=True,
)

port = os.environ.get("WAN2GP_API_PORT", "7861")

print(f"Starting Wan2GP API on port {port}...")
api_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "wan2gp_api:app", "--host", "0.0.0.0", "--port", port],
    env=os.environ.copy(),
)

time.sleep(3)

cloudflared = shutil.which("cloudflared")
if not cloudflared:
    target = Path("/usr/local/bin/cloudflared")
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    print("Installing Cloudflare Tunnel...")
    urllib.request.urlretrieve(url, target)
    target.chmod(0o755)
    cloudflared = str(target)

print("Starting public HTTPS tunnel...")
tunnel_process = subprocess.Popen(
    [cloudflared, "tunnel", "--url", f"http://127.0.0.1:{port}"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

public_url = None
pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
start = time.time()
while time.time() - start < 60:
    line = tunnel_process.stdout.readline() if tunnel_process.stdout else ""
    if line:
        match = pattern.search(line)
        if match:
            public_url = match.group(0)
            break
    if tunnel_process.poll() is not None:
        break

if not public_url:
    print("Could not automatically detect the Cloudflare URL.")
    print("The tunnel process is still running; inspect its output above.")
else:
    print("\n================ WAN2GP CHATGPT CONNECTION ================")
    print(f"Public API URL: {public_url}")
    print(f"OpenAPI base URL: {public_url}")
    print(f"Bearer API key: {api_key}")
    print("Keep the API key private. The URL changes when the Colab runtime restarts.")
    print("============================================================\n")

try:
    while api_process.poll() is None and tunnel_process.poll() is None:
        time.sleep(2)
except KeyboardInterrupt:
    pass
finally:
    for process in (tunnel_process, api_process):
        if process.poll() is None:
            process.terminate()
