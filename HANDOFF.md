# Parish Record Reader — current state

> Supersedes the original "no code yet" brief. Kept short on purpose;
> README.md is the user-facing doc.

## What exists

- Local pipeline runs end to end offline with the mock engine:
  `python -m parish_record_reader.cli samples/dummy_record.jpg`
  writes a filled PDF plus JSON sidecar and preprocessed PNG.
- Preprocessing: page-aware crop, Hough-based deskew, size cap
  (2048px), color-preserving CLAHE. `benchmark_variants()` returns
  raw vs. preprocessed PNGs for per-model CER/WER comparison.
- Two-step flow for human review: `transcribe_image()` returns the
  image + transcription/fields as data; `render_pdf()` builds the
  PDF from (edited) fields. `run_pipeline()` composes both.
- PDF: bundled DejaVu Sans (Unicode) so em-dashes, curly quotes,
  long s (ſ), and combining marks render. `build_filled_pdf()` fills
  the bilingual US-Letter AcroForm in `parish_record_reader/assets/`
  when pypdf is available and falls back to a generated document.
- Fields cover baptisms, marriages, and burials, with per-field
  confidence (`field_confidence`) and normalized name variants
  (`normalized_names`) alongside the original spelling.
- Modal endpoints: `POST /transcribe` (JSON for review),
  `POST /render` (JSON -> PDF), `POST /process` (one-shot),
  `GET /health`. CPU work runs via `run_in_threadpool`.

## Not yet done

- Real Fireworks transcription engine (Day 2). Confirm the default
  model in `parish_record_reader/config.py`
  (`DEFAULT_FIREWORKS_MODEL`) is still offered before depending on it.
- Review web UI (the JSON endpoints above are its backend contract).
- 30-page CER/WER benchmark across models.
- Demo video.

## Decisions kept from the original brief

Vision-language model over classical OCR; Fireworks for inference,
Baseten for benchmarking, Modal for the backend; prompt in Spanish
with record-type hint; mark illegible words `[ilegible]`.
