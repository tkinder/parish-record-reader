"""Day 1 exit test: a dummy record image produces a bilingual PDF."""
from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

from parish_record_reader.pipeline import run_pipeline
from parish_record_reader.preprocessing import preprocess_image


def _dummy_record_image() -> bytes:
    image = Image.new("RGB", (900, 1100), "white")
    draw = ImageDraw.Draw(image)
    lines = [
        "En la parroquia de San Jose, a catorce de marzo de",
        "mil ochocientos ochenta, bautice solemnemente a",
        "una nina a quien puse por nombre Maria Guadalupe,",
        "hija legitima de Jose Hernandez y Maria Garcia.",
    ]
    y = 80
    for line in lines:
        draw.text((70, y), line, fill=(30, 30, 30))
        y += 46
    image = image.rotate(2.5, resample=Image.BICUBIC, fillcolor="white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def test_dummy_record_produces_pdf() -> None:
    outcome = run_pipeline(_dummy_record_image())

    assert outcome.preprocessed_image_png.startswith(b"\x89PNG")
    assert outcome.pdf_bytes.startswith(b"%PDF")
    assert len(outcome.pdf_bytes) > 1000
    assert outcome.result.model_name == "mock-day1"
    assert outcome.result.fields.principal_name.startswith("[MOCK]")
    assert "María Guadalupe" in outcome.result.transcription_es
    assert "[ilegible]" in outcome.result.transcription_es


def test_preprocess_rejects_non_image() -> None:
    with pytest.raises(ValueError):
        preprocess_image(b"this is not an image")
