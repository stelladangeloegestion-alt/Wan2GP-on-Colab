"""Small authenticated HTTP API for WanGP running in Google Colab.

This uses WanGP's official in-process API (shared.api) instead of driving the
Gradio UI. It is intended to be started after the Colab notebook has installed
WanGP and its dependencies.
"""
from __future__ import annotations

import os
import secrets
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

WAN_ROOT = Path(os.environ.get("WAN2GP_ROOT", "/content/Wan2GP")).resolve()
OUTPUT_DIR = Path(os.environ.get("WAN_OUTPUTS_DIR", "/content/Wan2GP-data/outputs")).resolve()
API_KEY = os.environ.get("WAN2GP_API_KEY", "")

if not API_KEY:
    raise RuntimeError("WAN2GP_API_KEY is not set. Set a strong random API key before starting the server.")

app = FastAPI(title="Wan2GP Colab API", version="1.0")
_session = None
_session_lock = threading.Lock()
_jobs: dict[str, Any] = {}


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    model_type: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: str


def require_key(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {API_KEY}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def get_session():
    global _session
    with _session_lock:
        if _session is None:
            from shared.api import init
            _session = init(root=WAN_ROOT, output_dir=OUTPUT_DIR, console_output=True)
        return _session


def run_job(job_id: str, settings: dict[str, Any]) -> None:
    try:
        session = get_session()
        job = session.submit_task(settings)
        _jobs[job_id] = {"status": "running", "job": job}
        result = job.result()
        files = [str(Path(p).resolve()) for p in (result.generated_files or [])]
        _jobs[job_id] = {"status": "completed", "files": files}
    except Exception as exc:
        _jobs[job_id] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "wan2gp", "root": str(WAN_ROOT)}


@app.post("/generate", response_model=JobResponse, dependencies=[Depends(require_key)])
def generate(request: GenerateRequest) -> JobResponse:
    session = get_session()
    settings = dict(request.settings)
    if request.model_type:
        settings["model_type"] = request.model_type
    if "model_type" not in settings:
        settings["model_type"] = "t2v-A14B"
    settings["prompt"] = request.prompt

    # Validate/fill the model-specific defaults without forcing the caller to
    # reproduce the full WanGP settings object.
    defaults = session.get_default_settings(settings["model_type"])
    defaults.update(settings)
    settings = defaults

    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "queued"}
    threading.Thread(target=run_job, args=(job_id, settings), daemon=True).start()
    return JobResponse(job_id=job_id)


@app.get("/jobs/{job_id}", dependencies=[Depends(require_key)])
def job_status(job_id: str) -> dict[str, Any]:
    state = _jobs.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown job")
    response = {"job_id": job_id, "status": state["status"]}
    if state["status"] == "completed":
        response["files"] = state["files"]
    if state["status"] == "failed":
        response["error"] = state["error"]
    return response


@app.get("/download/{job_id}/{index}", dependencies=[Depends(require_key)])
def download(job_id: str, index: int) -> FileResponse:
    state = _jobs.get(job_id)
    if not state or state.get("status") != "completed":
        raise HTTPException(status_code=404, detail="Completed job not found")
    files = state.get("files", [])
    if index < 0 or index >= len(files):
        raise HTTPException(status_code=404, detail="Output not found")
    path = Path(files[index])
    if not path.is_file() or OUTPUT_DIR not in path.parents:
        raise HTTPException(status_code=404, detail="Output file unavailable")
    return FileResponse(path, filename=path.name)
