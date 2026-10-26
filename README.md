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

- [ ] Image upload and preprocessing (crop, deskew, contrast)
- [ ] Transcription pipeline
- [ ] Translation and field extraction
- [ ] Accuracy benchmark (CER/WER) across models
- [ ] Bilingual PDF generation
- [ ] Simple web interface
- [ ] Demo video

## Getting started

Setup instructions will be added as the code lands.

## Author

Terry Kinder ([@tkinder](https://github.com/tkinder))
