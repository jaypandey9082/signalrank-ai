from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class PacketResult:
    out_dir: Path
    copied: list[Path]
    notes: list[str]


def prepare_packet(
    csv_path: str | Path,
    xlsx_path: str | Path,
    deck_path: str | Path,
    out_dir: str | Path,
    root: str | Path = ROOT,
) -> PacketResult:
    root_path = Path(root)
    output_dir = _resolve(root_path, out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    notes: list[str] = []

    for source, target_name in [
        (_resolve(root_path, csv_path), "submission.csv"),
        (_resolve(root_path, xlsx_path), "submission.xlsx"),
        (root_path / "SUBMISSION_PACKET.md", "SUBMISSION_PACKET.md"),
        (root_path / "FINAL_SUBMISSION_CHECKLIST.md", "FINAL_SUBMISSION_CHECKLIST.md"),
    ]:
        if source.exists():
            copied.append(_copy_file(source, output_dir / target_name))
        else:
            notes.append(f"Missing optional/expected file: {source}")

    deck = _resolve(root_path, deck_path)
    if deck.exists():
        copied.append(_copy_file(deck, output_dir / deck.name))
    else:
        html_deck = root_path / "deck/approach_deck.html"
        if html_deck.exists():
            copied.append(_copy_file(html_deck, output_dir / "approach_deck.html"))
            notes.append("PDF deck missing; included HTML deck. Export it manually with Print -> Save as PDF.")
        else:
            notes.append("No PDF or HTML deck found.")

    manifest = output_dir / "MANIFEST.md"
    manifest.write_text(_manifest_text(copied, notes), encoding="utf-8")
    copied.append(manifest)
    return PacketResult(output_dir, copied, notes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare local hackathon submission packet.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--xlsx", required=True)
    parser.add_argument("--deck", required=True)
    parser.add_argument("--out-dir", default="submission_packet")
    args = parser.parse_args()

    result = prepare_packet(args.csv, args.xlsx, args.deck, args.out_dir)
    print(f"Prepared packet in {result.out_dir}")
    for path in result.copied:
        print(f"- {path.name}")
    for note in result.notes:
        print(f"Note: {note}")
    return 0


def _copy_file(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _manifest_text(copied: list[Path], notes: list[str]) -> str:
    lines = ["# SignalRank Submission Packet Manifest", "", "## Files"]
    lines.extend(f"- `{path.name}`" for path in copied)
    if notes:
        lines.extend(["", "## Notes"])
        lines.extend(f"- {note}" for note in notes)
    lines.extend(
        [
            "",
            "## Excluded",
            "- `candidates.jsonl`",
            "- debug outputs",
            "- benchmark outputs",
        ]
    )
    return "\n".join(lines) + "\n"


def _resolve(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


if __name__ == "__main__":
    raise SystemExit(main())
