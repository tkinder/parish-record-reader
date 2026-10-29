"""Pipeline orchestration with a human-review split.

Step 1 (``transcribe_image``) returns the preprocessed image and the
machine transcription/fields as data the review screen can edit.
Step 2 (``render_pdf``) builds the final PDF from the (possibly
edited) result. ``run_pipeline`` composes both for callers that do
not need the review pause and keeps the original one-shot behavior.
"""
from __future__ import annotations

from .models import PipelineResult, TranscriptionResult
from .pdfgen import build_filled_pdf, build_pdf
from .preprocessing import preprocess_image
from .transcription import Transcriber, get_transcriber

__all__ = ["render_pdf", "run_pipeline", "transcribe_image"]


def transcribe_image(
    image_bytes: bytes,
    *,
    transcriber: Transcriber | None = None,
    record_hint: str = "",
    engine: str = "mock",
) -> tuple[bytes, TranscriptionResult]:
    """Step 1: preprocess + transcribe. Returns (image_png, result)."""
    preprocessed = preprocess_image(image_bytes)
    active = transcriber if transcriber is not None else get_transcriber(engine)
    result = active.transcribe(preprocessed, record_hint=record_hint)
    return preprocessed, result


def render_pdf(result: TranscriptionResult, *, fill_form: bool = True) -> bytes:
    """Step 2: build the final PDF from reviewed/edited fields."""
    if fill_form:
        return build_filled_pdf(result)
    return build_pdf(result)


def run_pipeline(
    image_bytes: bytes,
    *,
    transcriber: Transcriber | None = None,
    record_hint: str = "",
    engine: str = "mock",
) -> PipelineResult:
    preprocessed, result = transcribe_image(
        image_bytes,
        transcriber=transcriber,
        record_hint=record_hint,
        engine=engine,
    )
    return PipelineResult(
        preprocessed_image_png=preprocessed,
        result=result,
        pdf_bytes=render_pdf(result),
    )
