"""Modal app: two-step HTTP endpoints for the parish record pipeline.

Run from the project root (in the .venv):

    modal serve -m parish_record_reader.app   # temporary dev URL
    modal deploy -m parish_record_reader.app  # persistent deployment

Step 1 ``POST /transcribe`` (multipart field ``file``, query ``hint``)
returns JSON for the human-review screen: the preprocessed image
(base64 PNG), transcription, translation, and extracted fields.
Step 2 ``POST /render`` accepts that JSON (with reviewer edits) and
returns the filled bilingual PDF. ``POST /process`` keeps the old
one-shot image->PDF behavior. CPU-bound work runs in a thread pool so
the async endpoints never block the event loop.

Until a real transcription engine lands, every response is sample
output: JSON carries ``is_sample``/``sample_notice`` and PDF
responses carry ``X-Sample-Output: mock`` plus an in-PDF banner.

``create_fastapi_app()`` exposes the same handlers as a plain
FastAPI app so tests can exercise the real multipart upload path
with ``TestClient`` without a Modal deployment.
"""
from __future__ import annotations

import base64

import modal
from fastapi import FastAPI, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response

try:  # package import (modal serve -m parish_record_reader.app)
    from .models import SAMPLE_NOTICE, TranscriptionResult, is_sample_result
    from .pipeline import render_pdf, transcribe_image
except ImportError:  # direct file load (modal serve .../app.py)
    from parish_record_reader.models import (  # type: ignore[no-redef]
        SAMPLE_NOTICE,
        TranscriptionResult,
        is_sample_result,
    )
    from parish_record_reader.pipeline import render_pdf, transcribe_image  # type: ignore[no-redef]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("requirements.txt")
    .add_local_python_source("parish_record_reader")
)

app = modal.App("parish-record-reader", image=image)

_ENGINE = "mock"


def _pdf_response(pdf_bytes: bytes, *, sample: bool) -> Response:
    headers = {"Content-Disposition": 'attachment; filename="parish_record.pdf"'}
    if sample:
        headers["X-Sample-Output"] = "mock"
        headers["X-Sample-Notice"] = "mock-engine-sample-not-a-real-transcription"
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


async def transcribe_impl(file: UploadFile, hint: str = "") -> object:
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty upload"}, status_code=400)
    try:
        preprocessed, result = await run_in_threadpool(
            transcribe_image, data, record_hint=hint, engine=_ENGINE
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    payload = result.to_dict()
    payload["engine"] = _ENGINE
    payload["preprocessed_image_png_base64"] = base64.b64encode(
        preprocessed
    ).decode("ascii")
    headers = {"X-Sample-Output": "mock"} if result.is_sample else {}
    return JSONResponse(payload, headers=headers)


async def render_impl(payload: dict) -> object:  # type: ignore[type-arg]
    try:
        result = TranscriptionResult.from_dict(payload)
    except (TypeError, ValueError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    pdf_bytes = await run_in_threadpool(render_pdf, result)
    return _pdf_response(pdf_bytes, sample=is_sample_result(result))


async def process_impl(file: UploadFile, hint: str = "") -> object:
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty upload"}, status_code=400)
    try:
        _, result = await run_in_threadpool(
            transcribe_image, data, record_hint=hint, engine=_ENGINE
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    pdf_bytes = await run_in_threadpool(render_pdf, result)
    return _pdf_response(pdf_bytes, sample=result.is_sample)


def health_impl() -> dict[str, str]:
    return {"status": "ok", "engine": _ENGINE, "sample_notice": SAMPLE_NOTICE}


def create_fastapi_app() -> FastAPI:
    """Plain FastAPI app with the same handlers (tests / local use)."""
    api = FastAPI(title="parish-record-reader")
    api.post("/transcribe")(transcribe_impl)
    api.post("/render")(render_impl)
    api.post("/process")(process_impl)
    api.get("/health")(health_impl)
    return api


@app.function()
@modal.fastapi_endpoint(method="POST")
async def transcribe(file: UploadFile, hint: str = "") -> object:
    return await transcribe_impl(file, hint)


@app.function()
@modal.fastapi_endpoint(method="POST")
async def render(payload: dict) -> object:  # type: ignore[type-arg]
    return await render_impl(payload)


@app.function()
@modal.fastapi_endpoint(method="POST")
async def process_record(file: UploadFile, hint: str = "") -> object:
    return await process_impl(file, hint)


@app.function()
@modal.fastapi_endpoint(method="GET")
def health() -> dict[str, str]:
    return health_impl()
