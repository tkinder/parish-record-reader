"""Generate the filled bilingual genealogy PDF from a transcription result."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

from .models import SAMPLE_NOTICE, TranscriptionResult, is_sample_result

_FONT_DIR = Path(__file__).resolve().parent / "fonts"
_FONT_FAMILY = "dejavu"
_TEMPLATE = (
    Path(__file__).resolve().parent
    / "assets"
    / "transcription-set-bilingual-US-Letter.pdf"
)


def _register_fonts(pdf: FPDF) -> None:
    """Embed the bundled DejaVu Sans Unicode font (regular + bold)."""
    regular = _FONT_DIR / "DejaVuSans.ttf"
    bold = _FONT_DIR / "DejaVuSans-Bold.ttf"
    if not regular.exists():
        raise FileNotFoundError(f"Bundled Unicode font not found: {regular}")
    pdf.add_font(_FONT_FAMILY, "", str(regular))
    if bold.exists():
        pdf.add_font(_FONT_FAMILY, "B", str(bold))
    # fpdf2 synthesizes an oblique from regular when no italic file exists;
    # register regular under "I" so set_font(..., "I") never falls back
    # to the built-in Helvetica.
    pdf.add_font(_FONT_FAMILY, "I", str(regular))


class _RecordPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(_FONT_FAMILY, "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Tu Árbol Familiar — Página {self.page_no()}", align="C")


def build_pdf(result: TranscriptionResult) -> bytes:
    """Render one record as a bilingual (Spanish/English) PDF document."""
    pdf = _RecordPDF(orientation="P", unit="mm", format="A4")
    _register_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    if is_sample_result(result):
        pdf.set_fill_color(180, 30, 30)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(_FONT_FAMILY, "B", 11)
        pdf.cell(
            0,
            9,
            "MUESTRA / SAMPLE — DATOS DE EJEMPLO (MOCK)",
            new_x="LMARGIN",
            new_y="NEXT",
            fill=True,
            align="C",
        )
        pdf.set_font(_FONT_FAMILY, "", 8)
        pdf.multi_cell(0, 5, SAMPLE_NOTICE, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    pdf.set_font(_FONT_FAMILY, "B", 18)
    pdf.cell(0, 10, "Registro Parroquial", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(_FONT_FAMILY, "", 12)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 7, "Parish Record — Tu Árbol Familiar", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font(_FONT_FAMILY, "B", 12)
    pdf.cell(0, 8, "Datos extraídos / Extracted data", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(_FONT_FAMILY, "", 10)
    for label_es, label_en, value in result.fields.display_rows():
        shown = value if value else "—"
        pdf.set_font(_FONT_FAMILY, "B", 10)
        pdf.cell(62, 6, f"{label_es} / {label_en}")
        pdf.set_font(_FONT_FAMILY, "", 10)
        pdf.multi_cell(0, 6, shown, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font(_FONT_FAMILY, "B", 12)
    pdf.cell(0, 8, "Transcripción / Transcription", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(_FONT_FAMILY, "", 10)
    pdf.multi_cell(0, 5.5, result.transcription_es or "—", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font(_FONT_FAMILY, "B", 12)
    pdf.cell(0, 8, "Traducción / Translation (English)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(_FONT_FAMILY, "", 10)
    pdf.multi_cell(0, 5.5, result.translation_en or "—", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font(_FONT_FAMILY, "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(
        0,
        5,
        f"Generado el / Generated on {date.today().isoformat()} — "
        f"Modelo / Model: {result.model_name}",
    )
    return bytes(pdf.output())


def _split_name(full: str) -> tuple[str, str, str]:
    """Split a display name into (given, surname1, surname2) best-effort.

    A leading ``[MOCK]`` sample marker is not part of the name; the
    sample warning travels in the transcription field instead, so the
    name boxes keep the readable name.
    """
    cleaned = (full or "").strip()
    if cleaned.upper().startswith("[MOCK]"):
        cleaned = cleaned[6:].strip()
    parts = cleaned.split()
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], parts[1], " ".join(parts[2:])


def _template_values(result: TranscriptionResult) -> dict[str, str]:
    """Map extracted fields onto the bilingual form's AcroForm names.

    Page 1 is baptism, page 2 marriage, page 3 burial. Only the page
    matching ``record_type`` receives the person-specific values; the
    transcription/translation are written to that same page. Matching
    is accent/case-insensitive and falls back to baptism.
    """
    f = result.fields
    kind = (f.record_type or "").lower()
    page = "p1"
    if any(k in kind for k in ("matrim", "marriage", "casamiento")):
        page = "p2"
    elif any(k in kind for k in ("defun", "burial", "entierro", "óbito", "obito")):
        page = "p3"

    sample = is_sample_result(result)
    transcription = result.transcription_es
    translation = result.translation_en
    if sample:
        # Unmistakable inside the form itself, not just in metadata.
        marker = "[MUESTRA / SAMPLE — MOCK DATA] "
        if not transcription.startswith("[MUESTRA"):
            transcription = marker + transcription
        if not translation.startswith("[SAMPLE"):
            translation = "[SAMPLE — MOCK DATA] " + translation

    values: dict[str, str] = {}
    prefix = f"transcription-set.{page}."
    values[prefix + "transcription"] = transcription
    values[prefix + "translation"] = translation
    values[prefix + "priest"] = f.priest_name
    values[prefix + "reg"] = f.parish
    values[prefix + "town"] = f.place
    values[prefix + "book"] = f.book
    values[prefix + "folio"] = f.folio
    values[prefix + "entry"] = f.entry_number
    values[prefix + "url"] = f.source_url
    values[prefix + "margin"] = f.margin_notes or f.notes

    def check(name: str, selected: bool) -> None:
        if selected:
            values[prefix + name] = "/Yes"

    if page == "p1":
        given, _, _ = _split_name(f.principal_name)
        f_given, f_s1, f_s2 = _split_name(f.father_name)
        m_given, m_s1, m_s2 = _split_name(f.mother_name)
        values[prefix + "bdate"] = f.event_date
        values[prefix + "ndate"] = f.birth_date
        values[prefix + "given"] = given
        values[prefix + "f_given"] = f_given
        values[prefix + "f_sur1"] = f_s1
        values[prefix + "f_sur2"] = f_s2
        values[prefix + "f_orig"] = f.father_origin
        values[prefix + "f_res"] = f.father_residence
        values[prefix + "m_given"] = m_given
        values[prefix + "m_sur1"] = m_s1
        values[prefix + "m_sur2"] = m_s2
        values[prefix + "m_orig"] = f.mother_origin
        values[prefix + "m_res"] = f.mother_residence
        values[prefix + "pgf"] = f.paternal_grandfather_name
        values[prefix + "pgm"] = f.paternal_grandmother_name
        values[prefix + "mgf"] = f.maternal_grandfather_name
        values[prefix + "mgm"] = f.maternal_grandmother_name
        values[prefix + "godf"] = f.godfather_name
        values[prefix + "godm"] = f.godmother_name
        values[prefix + "godrel"] = f.godparents_note
        values[prefix + "calidad"] = f.calidad
        legit = (f.legitimacy or "").lower()
        check("legit_0", "legít" in legit or "legit" in legit)
        check("legit_1", "natural" in legit)
        check("legit_2", "expós" in legit or "expos" in legit)
        check("legit_3", "no se indica" in legit or "not stated" in legit)
    elif page == "p2":
        g_given, g_s1, g_s2 = _split_name(f.groom_name or f.principal_name)
        b_given, b_s1, b_s2 = _split_name(f.bride_name)
        values[prefix + "mdate"] = f.event_date
        values[prefix + "banns"] = f.banns
        values[prefix + "disp"] = f.dispensation
        values[prefix + "vel"] = f.velacion_date
        values[prefix + "g_given"] = g_given
        values[prefix + "g_sur1"] = g_s1
        values[prefix + "g_sur2"] = g_s2
        values[prefix + "g_age"] = f.groom_age
        values[prefix + "g_marital"] = f.groom_marital_status
        values[prefix + "g_widow"] = f.groom_widow_of
        values[prefix + "g_orig"] = f.groom_origin
        values[prefix + "g_res"] = f.groom_residence
        values[prefix + "g_father"] = f.father_name
        values[prefix + "g_mother"] = f.mother_name
        values[prefix + "b_given"] = b_given
        values[prefix + "b_sur1"] = b_s1
        values[prefix + "b_sur2"] = b_s2
        values[prefix + "b_age"] = f.bride_age
        values[prefix + "b_marital"] = f.bride_marital_status
        values[prefix + "b_widow"] = f.bride_widow_of
        values[prefix + "b_orig"] = f.bride_origin
        values[prefix + "b_res"] = f.bride_residence
        values[prefix + "b_father"] = f.bride_father_name
        values[prefix + "b_mother"] = f.bride_mother_name
        values[prefix + "spons"] = "; ".join(f.wedding_sponsors)
        values[prefix + "wit"] = "; ".join(f.witnesses)
    else:
        given, s1, s2 = _split_name(f.deceased_name or f.principal_name)
        values[prefix + "given"] = given
        values[prefix + "sur1"] = s1
        values[prefix + "sur2"] = s2
        values[prefix + "age"] = f.age_at_death
        values[prefix + "marital"] = f.marital_status
        values[prefix + "spouse"] = f.spouse_name
        values[prefix + "orig"] = f.origin
        values[prefix + "res"] = f.residence
        values[prefix + "father"] = f.father_name
        values[prefix + "mother"] = f.mother_name
        values[prefix + "ddate"] = f.event_date
        values[prefix + "bdate"] = f.burial_date
        values[prefix + "bplace"] = f.burial_place
        values[prefix + "cause"] = f.cause_of_death
        kind_low = (f.deceased_kind or "").lower()
        check("kind_0", "adult" in kind_low)
        check("kind_1", "párv" in kind_low or "parv" in kind_low or "child" in kind_low)
        rites = (f.last_rites or "").lower()
        check("sacr_0", rites in ("sí", "si", "yes"))
        check("sacr_1", rites == "no")
        check("sacr_2", "no se indica" in rites or "not stated" in rites)
        will = (f.made_will or "").lower()
        check("will_0", "hizo" in will or will in ("sí", "si", "yes"))
        check("will_1", "no test" in will or will == "no")
        check("will_2", "no se indica" in will or "not stated" in will)
    return {k: v for k, v in values.items() if v}


def fill_template_pdf(
    result: TranscriptionResult, template_path: Path | None = None
) -> bytes:
    """Fill the bilingual US-Letter AcroForm and return PDF bytes.

    Raises FileNotFoundError when the template is absent and ImportError
    when pypdf is unavailable, so callers can fall back to build_pdf().
    """
    from pypdf import PdfReader, PdfWriter  # local: optional at import time

    template = template_path or _TEMPLATE
    if not template.exists():
        raise FileNotFoundError(f"Form template not found: {template}")
    reader = PdfReader(str(template))
    writer = PdfWriter()
    writer.append(reader)
    values = _template_values(result)
    for page in writer.pages:
        writer.update_page_form_field_values(page, values, auto_regenerate=False)
    import io

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_filled_pdf(result: TranscriptionResult) -> bytes:
    """Fill the US-Letter form when possible, else render a document.

    The demo's real output is the filled form; the generated document
    remains the fallback for environments without the template/pypdf.
    """
    try:
        return fill_template_pdf(result)
    except (FileNotFoundError, ImportError):
        return build_pdf(result)
