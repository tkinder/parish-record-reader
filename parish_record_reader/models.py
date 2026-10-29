"""Shared data structures for a transcribed parish record."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

# (attribute name, Spanish label, English label) in PDF display order.
FIELD_SPECS: tuple[tuple[str, str, str], ...] = (
    ("record_type", "Tipo de registro", "Record type"),
    ("parish", "Parroquia", "Parish"),
    ("place", "Lugar", "Place"),
    ("event_date", "Fecha", "Date"),
    ("birth_date", "Fecha de nacimiento", "Birth date"),
    ("principal_name", "Nombre principal", "Principal name"),
    ("father_name", "Padre", "Father"),
    ("mother_name", "Madre", "Mother"),
    ("godfather_name", "Padrino", "Godfather"),
    ("godmother_name", "Madrina", "Godmother"),
    ("groom_name", "Esposo / Contrayente", "Groom"),
    ("bride_name", "Esposa / Contrayente", "Bride"),
    ("deceased_name", "Difunto/a", "Deceased"),
    ("age_at_death", "Edad al fallecer", "Age at death"),
    ("spouse_name", "Cónyuge", "Spouse"),
    ("burial_date", "Fecha de entierro", "Burial date"),
    ("burial_place", "Lugar de entierro", "Burial place"),
    ("cause_of_death", "Causa de muerte", "Cause of death"),
    ("witnesses", "Testigos", "Witnesses"),
    ("priest_name", "Sacerdote", "Priest"),
    ("book", "Libro", "Book"),
    ("folio", "Folio", "Folio"),
    ("entry_number", "Partida", "Entry"),
    ("source_url", "URL de la fuente", "Source URL"),
    ("margin_notes", "Notas al margen", "Margin notes"),
    ("notes", "Notas", "Notes"),
    ("origin", "Natural de", "Native of"),
    ("residence", "Vecino/a de", "Resident of"),
    ("father_origin", "Padre — natural de", "Father — native of"),
    ("father_residence", "Padre — vecino de", "Father — resident of"),
    ("mother_origin", "Madre — natural de", "Mother — native of"),
    ("mother_residence", "Madre — vecina de", "Mother — resident of"),
    ("paternal_grandfather_name", "Abuelo paterno", "Paternal grandfather"),
    ("paternal_grandmother_name", "Abuela paterna", "Paternal grandmother"),
    ("maternal_grandfather_name", "Abuelo materno", "Maternal grandfather"),
    ("maternal_grandmother_name", "Abuela materna", "Maternal grandmother"),
    ("godparents_note", "Padrinos — vecinos o parentesco", "Godparents — residence/kinship"),
    ("legitimacy", "Legitimidad", "Legitimacy"),
    ("calidad", "Calidad o casta", "Classification (calidad)"),
    ("groom_age", "Novio — edad", "Groom — age"),
    ("groom_marital_status", "Novio — estado civil", "Groom — marital status"),
    ("groom_widow_of", "Novio — viudo de", "Groom — widower of"),
    ("groom_origin", "Novio — natural de", "Groom — native of"),
    ("groom_residence", "Novio — vecino de", "Groom — resident of"),
    ("bride_father_name", "Padre de la novia", "Bride's father"),
    ("bride_mother_name", "Madre de la novia", "Bride's mother"),
    ("bride_age", "Novia — edad", "Bride — age"),
    ("bride_marital_status", "Novia — estado civil", "Bride — marital status"),
    ("bride_widow_of", "Novia — viuda de", "Bride — widow of"),
    ("bride_origin", "Novia — natural de", "Bride — native of"),
    ("bride_residence", "Novia — vecina de", "Bride — resident of"),
    ("banns", "Amonestaciones", "Banns"),
    ("dispensation", "Dispensa y parentesco", "Dispensation & kinship"),
    ("velacion_date", "Velación", "Nuptial blessing date"),
    ("deceased_kind", "Difunto/a es", "Deceased is (adult/child)"),
    ("marital_status", "Estado civil", "Marital status"),
    ("last_rites", "Sacramentos recibidos", "Last rites received"),
    ("made_will", "Testamento", "Made a will"),
)


def _coerce_text(name: str, value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    raise TypeError(f"Field {name!r} must be text, got {type(value).__name__}")


def _coerce_witnesses(value: object, name: str = "witnesses") -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError(
                    f"Field {name!r} must contain only text, "
                    f"got {type(item).__name__}"
                )
            result.append(item)
        return result
    raise TypeError(
        f"Field {name!r} must be a list of text, got {type(value).__name__}"
    )


def _coerce_confidence(value: object) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(
            f"Field 'field_confidence' must be an object, got {type(value).__name__}"
        )
    result: dict[str, float] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            raise TypeError("Field 'field_confidence' keys must be text")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise TypeError(
                f"Confidence for {key!r} must be a number, got {type(raw).__name__}"
            )
        score = float(raw)
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Confidence for {key!r} must be between 0 and 1")
        result[key] = score
    return result


def _coerce_str_map(name: str, value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"Field {name!r} must be an object, got {type(value).__name__}")
    result: dict[str, str] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, str):
            raise TypeError(f"Field {name!r} must map text to text")
        result[key] = raw
    return result


@dataclass
class RecordFields:
    """Genealogy facts extracted from one parish record.

    Covers baptisms, marriages, and burials. Fields that do not apply to
    a record type are left blank. ``principal_name`` keeps the original
    spelling from the page; ``normalized_names`` optionally holds a
    modernized form per attribute (e.g. ``{"principal_name": "..."}``)
    so review can show both without overwriting the transcription.
    ``field_confidence`` holds a 0-1 model confidence per attribute.
    """

    record_type: str = ""
    parish: str = ""
    place: str = ""
    event_date: str = ""
    birth_date: str = ""
    principal_name: str = ""
    father_name: str = ""
    mother_name: str = ""
    godfather_name: str = ""
    godmother_name: str = ""
    groom_name: str = ""
    bride_name: str = ""
    deceased_name: str = ""
    age_at_death: str = ""
    spouse_name: str = ""
    burial_date: str = ""
    burial_place: str = ""
    cause_of_death: str = ""
    witnesses: list[str] = field(default_factory=list)
    priest_name: str = ""
    book: str = ""
    folio: str = ""
    entry_number: str = ""
    source_url: str = ""
    margin_notes: str = ""
    notes: str = ""
    origin: str = ""
    residence: str = ""
    father_origin: str = ""
    father_residence: str = ""
    mother_origin: str = ""
    mother_residence: str = ""
    paternal_grandfather_name: str = ""
    paternal_grandmother_name: str = ""
    maternal_grandfather_name: str = ""
    maternal_grandmother_name: str = ""
    godparents_note: str = ""
    legitimacy: str = ""
    calidad: str = ""
    groom_age: str = ""
    groom_marital_status: str = ""
    groom_widow_of: str = ""
    groom_origin: str = ""
    groom_residence: str = ""
    bride_father_name: str = ""
    bride_mother_name: str = ""
    bride_age: str = ""
    bride_marital_status: str = ""
    bride_widow_of: str = ""
    bride_origin: str = ""
    bride_residence: str = ""
    banns: str = ""
    dispensation: str = ""
    velacion_date: str = ""
    wedding_sponsors: list[str] = field(default_factory=list)
    deceased_kind: str = ""
    marital_status: str = ""
    last_rites: str = ""
    made_will: str = ""
    field_confidence: dict[str, float] = field(default_factory=dict)
    normalized_names: dict[str, str] = field(default_factory=dict)

    def display_rows(self) -> list[tuple[str, str, str]]:
        """Return (Spanish label, English label, value) rows for the PDF."""
        rows: list[tuple[str, str, str]] = []
        for attr, label_es, label_en in FIELD_SPECS:
            value = getattr(self, attr)
            if isinstance(value, list):
                value = "; ".join(value)
            rows.append((label_es, label_en, str(value)))
        return rows

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RecordFields":
        if not isinstance(data, dict):
            raise TypeError(
                f"RecordFields data must be an object, got {type(data).__name__}"
            )
        known = {spec[0] for spec in FIELD_SPECS} | {
            "field_confidence",
            "normalized_names",
        }
        values: dict[str, object] = {}
        for key, raw in data.items():
            if key not in known:
                continue
            if key in ("witnesses", "wedding_sponsors"):
                values[key] = _coerce_witnesses(raw, key)
            elif key == "field_confidence":
                values[key] = _coerce_confidence(raw)
            elif key == "normalized_names":
                values[key] = _coerce_str_map(key, raw)
            else:
                values[key] = _coerce_text(key, raw)
        return cls(**values)  # type: ignore[arg-type]


SAMPLE_NOTICE = (
    "MUESTRA / SAMPLE: datos de ejemplo del motor mock; "
    "no es una transcripción real. / Mock-engine sample data; "
    "not a real transcription."
)


def is_sample_result(result: "TranscriptionResult") -> bool:
    """True while output comes from the placeholder mock engine."""
    return (result.model_name or "").lower().startswith("mock")


@dataclass
class TranscriptionResult:
    """Verbatim transcription, translation, and extracted fields."""

    transcription_es: str
    translation_en: str
    fields: RecordFields
    model_name: str = "mock-day1"

    @property
    def is_sample(self) -> bool:
        return is_sample_result(self)

    def to_dict(self) -> dict[str, object]:
        return {
            "transcription_es": self.transcription_es,
            "translation_en": self.translation_en,
            "fields": self.fields.to_dict(),
            "model_name": self.model_name,
            "is_sample": self.is_sample,
            "sample_notice": SAMPLE_NOTICE if self.is_sample else "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TranscriptionResult":
        if not isinstance(data, dict):
            raise TypeError(
                f"TranscriptionResult data must be an object, got {type(data).__name__}"
            )
        raw_fields = data.get("fields", {})
        if raw_fields is None:
            raw_fields = {}
        if not isinstance(raw_fields, dict):
            raise TypeError(
                f"Field 'fields' must be an object, got {type(raw_fields).__name__}"
            )
        fields = RecordFields.from_dict(raw_fields)
        return cls(
            transcription_es=_coerce_text("transcription_es", data.get("transcription_es", "")),
            translation_en=_coerce_text("translation_en", data.get("translation_en", "")),
            fields=fields,
            model_name=_coerce_text("model_name", data.get("model_name", "unknown")) or "unknown",
        )


@dataclass
class PipelineResult:
    """Everything one pipeline run produced."""

    preprocessed_image_png: bytes
    result: TranscriptionResult
    pdf_bytes: bytes
