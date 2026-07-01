from __future__ import annotations

from scripts.prepare_submission_packet import prepare_packet


def test_prepare_submission_packet_copies_artifacts(tmp_path):
    root = _write_packet_project(tmp_path, with_pdf=True)
    out_dir = root / "submission_packet"

    result = prepare_packet("outputs/submission.csv", "outputs/submission.xlsx", "deck/SignalRank_AI_Approach_Deck.pdf", out_dir, root)

    assert (out_dir / "submission.csv").exists()
    assert (out_dir / "submission.xlsx").exists()
    assert (out_dir / "SignalRank_AI_Approach_Deck.pdf").exists()
    assert (out_dir / "MANIFEST.md").exists()
    assert all(path.name != "candidates.jsonl" for path in result.copied)


def test_prepare_submission_packet_handles_missing_pdf_gracefully(tmp_path):
    root = _write_packet_project(tmp_path, with_pdf=False)
    out_dir = root / "submission_packet"

    result = prepare_packet("outputs/submission.csv", "outputs/submission.xlsx", "deck/SignalRank_AI_Approach_Deck.pdf", out_dir, root)

    assert (out_dir / "approach_deck.html").exists()
    assert any("PDF deck missing" in note for note in result.notes)


def _write_packet_project(root, with_pdf: bool):
    for rel_path, content in [
        ("outputs/submission.csv", "candidate_id,rank,score,reasoning\nCAND_0000001,1,0.9,Good evidence.\n"),
        ("outputs/submission.xlsx", "xlsx"),
        ("SUBMISSION_PACKET.md", "packet"),
        ("FINAL_SUBMISSION_CHECKLIST.md", "checklist"),
        ("deck/approach_deck.html", "<html></html>"),
        ("candidates.jsonl", "{}\n"),
    ]:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if with_pdf:
        (root / "deck/SignalRank_AI_Approach_Deck.pdf").write_bytes(b"%PDF-1.4\n")
    return root
