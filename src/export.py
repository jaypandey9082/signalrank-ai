from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from src.submission import SubmissionRow, submission_rows_to_dicts
from src.utils import ensure_parent_dir


def write_submission_csv(rows: list[SubmissionRow], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        writer.writerows(submission_rows_to_dicts(rows))


def write_submission_xlsx(rows: list[SubmissionRow], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    data = [["candidate_id", "rank", "score", "reasoning"]]
    for row in rows:
        data.append([row.candidate_id, row.rank, row.score, row.reasoning])
    _write_minimal_xlsx(data, output_path)


def write_debug_csv(debug_rows: list[dict[str, Any]], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    fieldnames = sorted({key for row in debug_rows for key in row.keys()}) if debug_rows else ["candidate_id"]
    preferred = ["rank", "candidate_id", "score", "reasoning"]
    ordered = preferred + [field for field in fieldnames if field not in preferred]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ordered)
        writer.writeheader()
        writer.writerows(debug_rows)


def read_submission_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def compare_csv_xlsx(csv_path: str | Path, xlsx_path: str | Path) -> dict[str, Any]:
    csv_rows = read_submission_csv(csv_path)
    xlsx_rows = _read_minimal_xlsx(xlsx_path)
    issues: list[str] = []
    csv_columns = ["candidate_id", "rank", "score", "reasoning"]
    xlsx_columns = list(xlsx_rows[0].keys()) if xlsx_rows else []
    if xlsx_columns != csv_columns:
        issues.append(f"columns differ: csv={csv_columns}, xlsx={xlsx_columns}")
    if len(csv_rows) != len(xlsx_rows):
        issues.append(f"row count differs: csv={len(csv_rows)}, xlsx={len(xlsx_rows)}")
    for index, (csv_row, xlsx_row) in enumerate(zip(csv_rows, xlsx_rows), start=1):
        for column in csv_columns:
            left = _normalize_cell(csv_row.get(column), column)
            right = _normalize_cell(xlsx_row.get(column), column)
            if left != right:
                issues.append(f"row {index} column {column} differs")
                break
    return {
        "passed": not issues,
        "csv_row_count": len(csv_rows),
        "xlsx_row_count": len(xlsx_rows),
        "columns_match": xlsx_columns == csv_columns,
        "issues": issues,
    }


def _write_minimal_xlsx(data: list[list[Any]], output_path: Path) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(data))


def _worksheet_xml(data: list[list[Any]]) -> str:
    rows = []
    widths = [18, 10, 12, 90]
    cols = "".join(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>' for idx, width in enumerate(widths, start=1))
    for row_idx, row in enumerate(data, start=1):
        cells = []
        for col_idx, value in enumerate(row, start=1):
            ref = f"{_col_letter(col_idx)}{row_idx}"
            style = ' s="1"' if row_idx == 1 else ""
            if isinstance(value, (int, float)) and not isinstance(value, bool) and col_idx in {2, 3} and row_idx > 1:
                cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{escape(str(value))}</t></is></c>')
        rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<cols>{cols}</cols>"
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        f'<sheetData>{"".join(rows)}</sheetData>'
        "</worksheet>"
    )


def _col_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )


def _rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="submission" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )


def _workbook_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        "</styleSheet>"
    )


def _read_minimal_xlsx(path: str | Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(Path(path), "r") as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml")
    root = ET.fromstring(sheet)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    matrix: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        values: list[str] = []
        for cell in row.findall("x:c", namespace):
            inline = cell.find("x:is/x:t", namespace)
            numeric = cell.find("x:v", namespace)
            values.append(inline.text if inline is not None and inline.text is not None else numeric.text if numeric is not None and numeric.text is not None else "")
        matrix.append(values)
    if not matrix:
        return []
    headers = matrix[0]
    return [dict(zip(headers, row)) for row in matrix[1:]]


def _normalize_cell(value: object, column: str) -> str:
    text = "" if value is None else str(value)
    if column == "score":
        try:
            return str(float(text))
        except ValueError:
            return text
    if column == "rank":
        try:
            return str(int(float(text)))
        except ValueError:
            return text
    return text
