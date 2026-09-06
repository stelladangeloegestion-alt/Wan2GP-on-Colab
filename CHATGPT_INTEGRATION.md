# ChatGPT → Wan2GP integration

This branch adds an authenticated HTTP API that runs inside the existing Wan2GP Colab runtime.

## What is included

- `wan2gp_api.py`: FastAPI service with `/health`, `/generate`, `/jobs/{job_id}` and `/download/{job_id}/{index}`.
- `start_wan2gp_api.py`: installs the small API dependencies and starts Uvicorn.
- The API calls Wan2GP through its in-process `shared.api` layer, rather than scraping or controlling the Gradio page.

## Colab

Run the normal notebook cells first so that `/content/Wan2GP` is installed and dependencies are ready.
Then, from a new Colab code cell:

```python
%cd /content/Wan2GP-on-Colab
!python start_wan2gp_api.py
```

The launcher prints a temporary API key if `WAN2GP_API_KEY` was not already configured. Do not publish that key.

## Important

This is the generation backend. A public HTTPS tunnel/connector is still required before an external assistant can call the Colab API directly. GitHub itself does not provide that HTTP bridge.

The API is intentionally authenticated and does not expose an unauthenticated generation endpoint.
