"""Transcription engines.

Day 1 ships a deterministic mock so the upload -> review -> PDF path can be
built and demoed before any inference credits are spent. The Fireworks Llama
vision engine implements the same protocol on Day 2.
"""
from __future__ import annotations

from typing import Protocol

from .models import RecordFields, TranscriptionResult


class Transcriber(Protocol):
    def transcribe(
        self, image_png: bytes, *, record_hint: str = ""
    ) -> TranscriptionResult: ...


class MockTranscriber:
    """Canned baptism result, clearly labeled as mock data."""

    model_name = "mock-day1"

    def transcribe(
        self, image_png: bytes, *, record_hint: str = ""
    ) -> TranscriptionResult:
        fields = RecordFields(
            record_type="Bautismo / Baptism",
            parish="[MOCK] Parroquia de San José",
            place="[MOCK] Guadalajara, Jalisco",
            event_date="1880-03-14",
            principal_name="[MOCK] María Guadalupe Hernández",
            father_name="[MOCK] José Hernández",
            mother_name="[MOCK] María de la Luz García",
            godfather_name="[MOCK] Antonio García",
            godmother_name="[MOCK] Rosa Martínez",
            witnesses=["[MOCK] Pedro López", "[MOCK] Juan Torres"],
            priest_name="[MOCK] Padre Miguel Santos",
            notes="Datos de ejemplo del motor mock (Día 1).",
        )
        return TranscriptionResult(
            transcription_es=(
                "[MOCK] En la parroquia de San José, a catorce de marzo de mil "
                "ochocientos ochenta, yo, el padre Miguel Santos, bauticé "
                "solemnemente a una niña que nació [ilegible], a quien puse por "
                "nombre María Guadalupe, hija legítima de José Hernández y de "
                "María de la Luz García. Fueron sus padrinos Antonio García y "
                "Rosa Martínez, a quienes advertí el parentesco espiritual."
            ),
            translation_en=(
                "[MOCK] In the parish of San José, on the fourteenth of March, "
                "one thousand eight hundred eighty, I, Father Miguel Santos, "
                "solemnly baptized a girl who was born [illegible], whom I named "
                "María Guadalupe, legitimate daughter of José Hernández and "
                "María de la Luz García. Her godparents were Antonio García and "
                "Rosa Martínez, whom I advised of the spiritual kinship."
            ),
            fields=fields,
            model_name=self.model_name,
        )


def get_transcriber(name: str = "mock") -> Transcriber:
    if name == "mock":
        return MockTranscriber()
    if name == "fireworks":
        raise NotImplementedError(
            "Fireworks Llama vision transcription is scheduled for Day 2."
        )
    raise ValueError(f"Unknown transcriber: {name!r}")
