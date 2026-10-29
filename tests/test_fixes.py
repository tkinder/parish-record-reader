"""Regression tests for the review fixes (Unicode PDF, fields, endpoints)."""
from __future__ import annotations

import asyncio
import io
import json

import pytest
from PIL import Image, ImageDraw

from parish_record_reader.cli import main as cli_main
from parish_record_reader.models import RecordFields, TranscriptionResult
from parish_record_reader.pdfgen import build_filled_pdf, build_pdf, fill_template_pdf
from parish_record_reader.pipeline import render_pdf, transcribe_image
from parish_record_reader.preprocessing import _deskew_angle, preprocess_image

SPECIAL = "José — “María” ſ á bauticé"


def _result(transcription: str = SPECIAL) -> TranscriptionResult:
    return TranscriptionResult(
        transcription_es=transcription,
        translation_en="Joseph — “Mary” baptized",
        fields=RecordFields(
            record_type="Bautismo / Baptism",
            principal_name="María Guadalupe Hernández",
            event_date="1880-03-14",
            priest_name="Padre Miguel Santos",
        ),
        model_name="test",
    )


def _dummy_image(rotate: float = 0.0) -> bytes:
    image = Image.new("RGB", (900, 1100), "white")
    draw = ImageDraw.Draw(image)
    y = 80
    for line in ["En la parroquia de San Jose, a catorce de marzo de"] * 6:
        draw.text((70, y), line, fill=(30, 30, 30))
        y += 60
    if rotate:
        image = image.rotate(rotate, resample=Image.BICUBIC, fillcolor="white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def test_pdf_renders_unicode_characters() -> None:
    pdf_bytes = build_pdf(_result())
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_filled_form_keeps_unicode_values() -> None:
    from pypdf import PdfReader

    pdf_bytes = build_filled_pdf(_result())
    assert pdf_bytes.startswith(b"%PDF")
    fields = PdfReader(io.BytesIO(pdf_bytes)).get_fields() or {}
    assert fields["transcription-set.p1.transcription"]["/V"] == SPECIAL
    assert fields["transcription-set.p1.given"]["/V"] == "María"


def test_template_fill_marriage_page() -> None:
    from pypdf import PdfReader

    result = TranscriptionResult(
        transcription_es="Casamiento",
        translation_en="Marriage",
        fields=RecordFields(
            record_type="Matrimonio",
            groom_name="José Hernández",
            bride_name="María García",
            event_date="1881-05-02",
        ),
        model_name="test",
    )
    fields = PdfReader(io.BytesIO(fill_template_pdf(result))).get_fields() or {}
    assert fields["transcription-set.p2.g_given"]["/V"] == "José"
    assert fields["transcription-set.p2.b_given"]["/V"] == "María"


def test_deskew_detects_and_corrects_skew() -> None:
    import cv2
    import numpy as np

    skewed = _dummy_image(rotate=4.0)
    buffer = np.frombuffer(skewed, dtype=np.uint8)
    gray = cv2.cvtColor(cv2.imdecode(buffer, cv2.IMREAD_COLOR), cv2.COLOR_BGR2GRAY)
    assert abs(_deskew_angle(gray)) > 1.0
    # Preprocessing must not raise and must return a valid PNG.
    assert preprocess_image(skewed).startswith(b"\x89PNG")


def test_preprocess_caps_large_images() -> None:
    big = Image.new("RGB", (3000, 2000), "white")
    buffer = io.BytesIO()
    big.save(buffer, format="PNG")
    out = Image.open(io.BytesIO(preprocess_image(buffer.getvalue())))
    assert max(out.size) <= 2048


def test_from_dict_rejects_non_text_witnesses() -> None:
    with pytest.raises(TypeError):
        RecordFields.from_dict({"witnesses": ["Ana", 42]})
    with pytest.raises(TypeError):
        RecordFields.from_dict({"principal_name": 42})
    assert RecordFields.from_dict({"witnesses": "Ana"}).witnesses == ["Ana"]
    fields = RecordFields.from_dict(
        {"field_confidence": {"principal_name": 0.9}, "groom_name": "José"}
    )
    assert fields.groom_name == "José"
    assert fields.field_confidence["principal_name"] == 0.9
    with pytest.raises(ValueError):
        RecordFields.from_dict({"field_confidence": {"principal_name": 2.0}})


def test_two_step_review_roundtrip() -> None:
    _, result = transcribe_image(_dummy_image())
    payload = json.loads(json.dumps(result.to_dict()))
    payload["fields"]["principal_name"] = "Edited Name"
    edited = TranscriptionResult.from_dict(payload)
    assert render_pdf(edited).startswith(b"%PDF")


def test_cli_rejects_unknown_engine(tmp_path) -> None:  # type: ignore[no-untyped-def]
    image = tmp_path / "x.jpg"
    image.write_bytes(_dummy_image())
    with pytest.raises(SystemExit) as excinfo:
        cli_main([str(image), "--engine", "bogus"])
    assert excinfo.value.code == 2


def _saved_fields(pdf_bytes: bytes, tmp_path, name: str = "out.pdf"):  # type: ignore[no-untyped-def]
    from pypdf import PdfReader

    path = tmp_path / name
    path.write_bytes(pdf_bytes)
    assert path.read_bytes().startswith(b"%PDF")
    return PdfReader(str(path)).get_fields() or {}


def test_saved_filled_pdf_baptism(tmp_path) -> None:  # type: ignore[no-untyped-def]
    result = TranscriptionResult(
        transcription_es="Bauticé a María — ſ",
        translation_en="I baptized Mary",
        fields=RecordFields(
            record_type="Bautismo",
            parish="Parroquia de San José — ſ",
            place="Guadalajara, Jalisco",
            book="Libro 3",
            folio="Foja 12v",
            entry_number="Partida 45",
            event_date="1880-03-14",
            birth_date="1880-03-10",
            principal_name="María Guadalupe Hernández",
            father_name="José Hernández",
            mother_name="María García",
            godfather_name="Antonio García",
            godmother_name="Rosa Martínez",
            priest_name="Padre Miguel Santos",
            legitimacy="Legítimo",
        ),
        model_name="test-model",
    )
    fields = _saved_fields(build_filled_pdf(result), tmp_path)
    v = lambda k: fields[k]["/V"]  # noqa: E731
    assert v("transcription-set.p1.reg") == "Parroquia de San José — ſ"
    assert v("transcription-set.p1.town") == "Guadalajara, Jalisco"
    assert v("transcription-set.p1.given") == "María"
    assert v("transcription-set.p1.bdate") == "1880-03-14"
    assert v("transcription-set.p1.priest") == "Padre Miguel Santos"
    assert v("transcription-set.p1.legit_0") == "/Yes"
    # Other pages stay blank for a baptism.
    assert not (fields["transcription-set.p2.g_given"].get("/V") or "")


def test_saved_filled_pdf_burial(tmp_path) -> None:  # type: ignore[no-untyped-def]
    result = TranscriptionResult(
        transcription_es="Defunción de José",
        translation_en="Death of Joseph",
        fields=RecordFields(
            record_type="Defunción / Burial",
            deceased_name="José Hernández García",
            age_at_death="70 años",
            spouse_name="María García",
            event_date="1900-01-05",
            burial_date="1900-01-06",
            burial_place="Panteón municipal",
            cause_of_death="Fiebre — ſ",
            priest_name="Padre Miguel Santos",
            deceased_kind="Adulto",
            last_rites="Sí",
            made_will="No testó",
        ),
        model_name="test-model",
    )
    fields = _saved_fields(build_filled_pdf(result), tmp_path)
    v = lambda k: fields[k]["/V"]  # noqa: E731
    assert v("transcription-set.p3.given") == "José"
    assert v("transcription-set.p3.sur1") == "Hernández"
    assert v("transcription-set.p3.age") == "70 años"
    assert v("transcription-set.p3.cause") == "Fiebre — ſ"
    assert v("transcription-set.p3.kind_0") == "/Yes"
    assert v("transcription-set.p3.sacr_0") == "/Yes"
    assert v("transcription-set.p3.will_1") == "/Yes"


def test_sample_output_is_unmistakable(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, result = transcribe_image(_dummy_image())
    payload = result.to_dict()
    assert payload["is_sample"] is True
    assert "SAMPLE" in str(payload["sample_notice"])
    fields = _saved_fields(build_filled_pdf(result), tmp_path)
    transcription = fields["transcription-set.p1.transcription"]["/V"]
    assert transcription.startswith("[MUESTRA / SAMPLE")
    # The [MOCK] marker must not leak into the child's given-name box.
    assert fields["transcription-set.p1.given"]["/V"] == "María"
    # Generated (non-form) PDFs also build without error for mock data.
    assert build_pdf(result).startswith(b"%PDF")


def test_generated_pdf_unicode_names() -> None:
    result = TranscriptionResult(
        transcription_es="Ŝeñor — “test” ſ á",
        translation_en="Test — “x”",
        fields=RecordFields(
            record_type="Bautismo",
            principal_name="María-José Ñúñez — ſ",
            priest_name="Padre Ŝantos “el viejo”",
        ),
        model_name="test-model",
    )
    assert build_pdf(result).startswith(b"%PDF")


def test_upload_path_via_http_multipart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from parish_record_reader.app import create_fastapi_app

    client = TestClient(create_fastapi_app())
    image = _dummy_image()
    response = client.post(
        "/transcribe", files={"file": ("record.jpg", image, "image/jpeg")}
    )
    assert response.status_code == 200
    assert response.headers.get("x-sample-output") == "mock"
    payload = response.json()
    assert payload["is_sample"] is True
    assert payload["model_name"] == "mock-day1"
    assert payload["fields"]["principal_name"].startswith("[MOCK]")

    render_response = client.post("/render", json=payload)
    assert render_response.status_code == 200
    assert render_response.headers.get("x-sample-output") == "mock"
    fields = _saved_fields(render_response.content, tmp_path, "render.pdf")
    assert fields["transcription-set.p1.given"]["/V"] == "María"

    process_response = client.post(
        "/process", files={"file": ("record.jpg", image, "image/jpeg")}
    )
    assert process_response.status_code == 200
    assert process_response.headers.get("x-sample-output") == "mock"
    assert process_response.content.startswith(b"%PDF")

    empty = client.post("/transcribe", files={"file": ("x.jpg", b"", "image/jpeg")})
    assert empty.status_code == 400


def test_upload_endpoint_two_step() -> None:
    from fastapi import UploadFile

    from parish_record_reader import app as app_module

    upload = UploadFile(filename="x.jpg", file=io.BytesIO(_dummy_image()))
    response = asyncio.run(app_module.transcribe.local(upload, hint=""))
    assert response.status_code == 200
    payload = json.loads(bytes(response.body))
    assert payload["fields"]["principal_name"]
    assert payload["preprocessed_image_png_base64"]

    render_response = asyncio.run(app_module.render.local(payload))
    assert render_response.status_code == 200
    assert bytes(render_response.body).startswith(b"%PDF")
