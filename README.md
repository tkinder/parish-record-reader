# Tu Arbol Familiar: Parish Record Reader

Turn a photo of a handwritten Spanish or Latin parish record into a clean transcription, an English translation, and a filled bilingual genealogy record.

Built for the **Meta Global AI Developer Hackathon 2026** (Indie Dev Track, theme: *Build for Your World*).

> **Status:** In active development during the hackathon (Oct 26 to Nov 4, 2026).

## The problem

Families tracing Hispanic roots often hit a wall at old church records. Baptism, marriage, and burial entries from the 1600s to 1900s are handwritten in faded ink, in old Spanish or Latin, with abbreviations and spellings that even fluent speakers struggle to read. The names and dates are right there on the page, but most people can't get them out.

## What it does

1. **Upload a photo** of a parish record (baptism, marriage, or burial).
2. **Transcribe** the handwriting into text, keeping the original spelling.
3. **Translate** the record into English.
4. **Extract the key facts**: names, dates, places, parents, godparents, witnesses, priest.
5. **Fill a bilingual genealogy record** (Spanish and English) as a PDF, ready to save or print.

## How it works

- **Vision and language models:** Meta Llama models handle reading the page, transcription, translation, and field extraction.
- **Model testing on Baseten:** open-source vision and language models run on Baseten so they can be compared side by side with Llama.
- **Accuracy scoring:** every model is benchmarked on a 30-page test set of 1700s Spanish records with expert transcriptions, scored by character error rate (CER) and word error rate (WER).
- **PDF output:** extracted fields are written into a fillable bilingual genealogy form.

## Roadmap

- [x] Image preprocessing (crop, deskew, contrast)
- [ ] Image upload endpoint (code written; needs a live Modal run)
- [x] Transcription pipeline (mock engine; real model pending)
- [x] Translation and field extraction (mock data)
- [ ] Accuracy benchmark (CER/WER) across models
- [x] Bilingual PDF generation
- [ ] Simple web interface
- [ ] Demo video

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in provider keys as later phases need them
```

Day 1 runs fully offline with a mock transcription engine:

```bash
python -m parish_record_reader.cli samples/dummy_record.jpg
# writes outputs/dummy_record_record.pdf (+ JSON sidecar + preprocessed PNG)
pytest
```

To try the Modal-hosted endpoints (requires `modal setup` first):

```bash
modal serve -m parish_record_reader.app
# POST /transcribe  multipart field `file` -> JSON (image + fields) for review
# POST /render      edited JSON -> filled PDF
# POST /process     multipart field `file` -> filled PDF (one-shot)
```

## Author

Terry Kinder ([@tkinder](https://github.com/tkinder))
