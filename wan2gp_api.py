"""Small authenticated HTTP API for WanGP running in Google Colab."""
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

app = FastAPI(title="Wan2GP Colab API", version="1.1")
_session = None
_session_lock = threading.Lock()
_generation_lock = threading.Lock()
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


def choose_model_type(session, requested: str | None) -> str:
    if requested:
        return requested

    # Prefer a small 5B text/video-capable model for Colab/T4, then fall back
    # to the first text-to-video model exposed by the installed WanGP version.
    records = session.list_model_defs(limit=500)
    usable = []
    for record in records:
        model_type = str(record.get("model_type", ""))
        name = str(record.get("name", ""))
        text = f"{model_type} {name}".casefold()
        if "5b" in text and ("video" in text or "ti2v" in text or "t2v" in text):
            usable.append(model_type)

    for candidate in ("ti2v-5B", "t2v-5B"):
        if candidate in usable:
            return candidate
    if usable:
        return usable[0]

    for record in records:
        model_type = str(record.get("model_type", ""))
        text = f"{model_type} {record.get('name', '')}".casefold()
        if "t2v" in text or "text-to-video" in text:
            return model_type

    raise RuntimeError("No text-to-video model is available in this WanGP installation.")


def run_job(job_id: str, settings: dict[str, Any]) -> None:
    try:
        # WanGP protects its own generation path, but this extra lock makes the
        # HTTP service explicitly single-job so two clients cannot compete for
        # the same Colab GPU.
        with _generation_lock:
            _jobs[job_id] = {"status": "running"}
            session = get_session()
            job = session.submit_task(settings)
            result = job.result()
            files = [str(Path(p).resolve()) for p in (result.generated_files or [])]
            _jobs[job_id] = {"status": "completed", "files": files}
    except Exception as exc:
        _jobs[job_id] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "wan2gp"}


@app.get("/models", dependencies=[Depends(require_key)])
def models() -> dict[str, Any]:
    session = get_session()
    records = session.list_model_metadata(include_availability=False, limit=500)
    return {"models": records}


@app.post("/generate", response_model=JobResponse, dependencies=[Depends(require_key)])
def generate(request: GenerateRequest) -> JobResponse:
    session = get_session()
    model_type = choose_model_type(session, request.model_type)
    settings = session.get_default_settings(model_type)
    settings.update(request.settings)
    settings["model_type"] = model_type
    settings["prompt"] = request.prompt

    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "queued", "model_type": model_type}
    threading.Thread(target=run_job, args=(job_id, settings), daemon=True, name=f"wan2gp-{job_id[:8]}").start()
    return JobResponse(job_id=job_id)


@app.get("/jobs/{job_id}", dependencies=[Depends(require_key)])
def job_status(job_id: str) -> dict[str, Any]:
    state = _jobs.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown job")
    response = {"job_id": job_id, "status": state["status"]}
    if "model_type" in state:
        response["model_type"] = state["model_type"]
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
    path = Path(files[index]).resolve()
    if not path.is_file() or (path != OUTPUT_DIR and OUTPUT_DIR not in path.parents):
        raise HTTPException(status_code=404, detail="Output file unavailable")
    return FileResponse(path, filename=path.name)
