"""Local command line: run the pipeline on one image file.

Usage:
    python -m parish_record_reader.cli path/to/record.jpg [-o out.pdf]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ENGINES = ("mock", "fireworks")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Photo of the parish record")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path (default: outputs/<name>_record.pdf)",
    )
    parser.add_argument(
        "--engine",
        default="mock",
        choices=ENGINES,
        help="Transcription engine",
    )
    parser.add_argument(
        "--hint",
        default="",
        help="Context hint, e.g. 'acta de bautismo, Jalisco, ~1880'",
    )
    args = parser.parse_args(argv)

    from .pipeline import run_pipeline

    image_bytes = args.image.read_bytes()
    outcome = run_pipeline(
        image_bytes, record_hint=args.hint, engine=args.engine
    )

    output = args.output or Path("outputs") / f"{args.image.stem}_record.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(outcome.pdf_bytes)

    sidecar = output.with_suffix(".json")
    sidecar.write_text(
        json.dumps(outcome.result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    enhanced = output.with_name(f"{output.stem}_preprocessed.png")
    enhanced.write_bytes(outcome.preprocessed_image_png)

    print(f"PDF:          {output}")
    print(f"Fields JSON:  {sidecar}")
    print(f"Preprocessed: {enhanced}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
