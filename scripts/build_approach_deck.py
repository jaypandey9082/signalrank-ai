from __future__ import annotations

import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECK_DIR = ROOT / "deck"
HTML_PATH = DECK_DIR / "approach_deck.html"
PDF_PATH = DECK_DIR / "SignalRank_AI_Approach_Deck.pdf"


SLIDES = [
    ("SignalRank AI", ["Explainable Candidate Discovery Engine", "Redrob / Hack2skill Data & AI Challenge"]),
    ("Problem", ["Recruiting search fails when it ranks keywords instead of real fit.", "SignalRank AI separates shipped evidence from shallow AI buzzwords."]),
    ("What The JD Really Needs", ["Production ranking/search/retrieval", "Recommendation systems", "Embeddings/vector search", "Evaluation frameworks", "Product engineering ownership"]),
    ("System Architecture", ["Candidate data -> parsing -> features -> static fit", "-> Redrob behavior -> trap penalties -> ranking", "-> deterministic reasoning -> CSV/XLSX"]),
    ("Static Fit Scoring", ["Career evidence", "Retrieval/ranking evidence", "Skills as support", "Experience, product context, location, evaluation"]),
    ("Redrob Behavior Scoring", ["Recent activity", "Recruiter response rate", "Notice and relocation", "Profile trust and process reliability"]),
    ("Trap Defense", ["Wrong-role keyword stuffing", "Weak AI hype", "Impossible or inconsistent profile signals", "Non-target AI-only profiles"]),
    ("Reasoning", ["Specific, factual, JD-connected, concern-aware", "Deterministic evidence-based generation", "No hosted LLM calls during ranking"]),
    ("Runtime and Reproducibility", ["100K CSV-only run: about 3m16s-3m23s locally", "CPU-only", "No network during ranking", "Deterministic repeat hash"]),
    ("Demo and Submission", ["Public GitHub repo", "Streamlit sandbox", "Canonical CSV and synced XLSX", "PDF approach deck"]),
]


def build_pdf(pdf_path: str | Path = PDF_PATH) -> Path:
    output_path = Path(pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _build_with_reportlab(output_path)
    except ImportError:
        _build_minimal_pdf(output_path)
    return output_path


def main() -> int:
    if not HTML_PATH.exists():
        print("deck/approach_deck.html is missing. Open deck/approach_deck.md or recreate the HTML deck first.")
        return 1
    output = build_pdf(PDF_PATH)
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Wrote {output} ({size_mb:.2f} MB)")
    if size_mb > 5:
        print("Warning: PDF is over 5 MB.")
    return 0


def _build_with_reportlab(output_path: Path) -> None:
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    page_size = landscape(letter)
    pdf = canvas.Canvas(str(output_path), pagesize=page_size)
    width, height = page_size
    for title, bullets in SLIDES:
        pdf.setFont("Helvetica-Bold", 34)
        pdf.drawString(0.7 * inch, height - 1.0 * inch, title)
        pdf.setFont("Helvetica", 20)
        y = height - 1.55 * inch
        for bullet in bullets:
            wrapped = textwrap.wrap(bullet, width=72)
            for line_index, line in enumerate(wrapped):
                prefix = "- " if line_index == 0 else "  "
                pdf.drawString(0.9 * inch, y, prefix + line)
                y -= 0.32 * inch
            y -= 0.08 * inch
        pdf.setFont("Helvetica", 10)
        pdf.drawString(0.7 * inch, 0.35 * inch, "SignalRank AI")
        pdf.showPage()
    pdf.save()


def _build_minimal_pdf(output_path: Path) -> None:
    pages = [_page_stream(title, bullets) for title, bullets in SLIDES]
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_refs = " ".join(f"{3 + index * 2} 0 R" for index in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{page_refs}] /Count {len(pages)} >>".encode("ascii"))
    for index, stream in enumerate(pages):
        content_id = 4 + index * 2
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> /F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )
        stream_bytes = stream.encode("latin-1", errors="replace")
        objects.append(b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream")

    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, payload in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{object_id} 0 obj\n".encode("ascii"))
        data.extend(payload)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    output_path.write_bytes(bytes(data))


def _page_stream(title: str, bullets: list[str]) -> str:
    lines = ["BT", "/F2 34 Tf", "56 540 Td", f"({_escape_pdf(title)}) Tj", "/F1 20 Tf", "0 -50 Td"]
    for bullet in bullets:
        wrapped = textwrap.wrap(bullet, width=66) or [bullet]
        for line_index, line in enumerate(wrapped):
            prefix = "- " if line_index == 0 else "  "
            lines.append(f"({_escape_pdf(prefix + line)}) Tj")
            lines.append("0 -28 Td")
        lines.append("0 -8 Td")
    lines.extend(["/F1 10 Tf", "0 -28 Td", "(SignalRank AI) Tj", "ET"])
    return "\n".join(lines)


def _escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


if __name__ == "__main__":
    raise SystemExit(main())
