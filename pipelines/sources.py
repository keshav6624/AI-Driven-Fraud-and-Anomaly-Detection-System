"""Data source readers.

Reads tabular source files (CSV / XLSX) without ever modifying the originals.
XLSX files produced by some government portals contain malformed style sheets
that crash ``openpyxl``; in that case we fall back to a direct OOXML parse of
the worksheet XML, which recovers cell values reliably.
"""
from __future__ import annotations

import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

_SSM = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS = {"m": _SSM, "r": _RNS}


@dataclass(frozen=True)
class TableRead:
    """A raw table extracted from a source file, plus provenance metadata."""

    file_name: str
    sheet_name: str | None
    header_row_index: int  # 0-based row index of the detected header
    columns: list[str]
    records: list[dict[str, Any]]  # raw string values, header not included
    notes: list[str]


def _cell_value(c: ET.Element, shared: list[str]) -> Any:
    t = c.get("t")
    if t == "s":
        v = c.find("m:v", _NS)
        return shared[int(v.text)] if v is not None and v.text else None
    if t == "inlineStr":
        is_el = c.find("m:is", _NS)
        if is_el is None:
            return None
        return "".join(x.text or "" for x in is_el.iter(f"{{{_SSM}}}t"))
    v = c.find("m:v", _NS)
    if v is None:
        return None
    return v.text


def _col_index(ref: str | None) -> int:
    """Convert a cell reference like 'BC12' to a 0-based column index."""
    if not ref:
        return 0
    letters = re.match(r"([A-Z]+)", ref)
    idx = 0
    for ch in letters.group(1):
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def _iter_xlsx_rows(path: Path) -> Iterator[tuple[int, list[Any]]]:
    """Yield (row_index, values) for every sheet row, parsing the sheet XML."""
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", _NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{_SSM}}}t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        sheets = [
            (s.get("name"), s.get(f"{{{_RNS}}}id"))
            for s in wb.find("m:sheets", _NS)
        ]
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rel_map = {r.get("Id"): r.get("Target") for r in rels}
        # Sheet order in the archive is sheet1.xml, sheet2.xml, ... matching rel ids
        for i, (sheet_name, rid) in enumerate(sheets, start=1):
            target = rel_map.get(rid, f"worksheets/sheet{i}.xml")
            member = f"xl/{target}" if not target.startswith("xl/") else target
            root = ET.fromstring(z.read(member))
            for r_i, row in enumerate(root.iter(f"{{{_SSM}}}row")):
                cells: dict[int, Any] = {}
                for c in row:
                    cells[_col_index(c.get("r"))] = _cell_value(c, shared)
                if not cells:
                    yield r_i, []
                    continue
                width = max(cells) + 1
                values = [cells.get(j) for j in range(width)]
                yield r_i, values


def _norm_header(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v).strip()) if v is not None else ""


def _detect_header(rows: list[list[Any]], min_cols: int = 3) -> int:
    """Heuristic: first row where >= min_cols cells are non-numeric strings."""
    for i, row in enumerate(rows):
        nonnull = [v for v in row if _norm_header(v)]
        if len(nonnull) >= min_cols and all(
            not re.fullmatch(r"[\d,.\s]+", _norm_header(v)) for v in nonnull[:4]
        ):
            return i
    return 0


def read_table(path: Path) -> list[TableRead]:
    """Read a CSV or XLSX file into raw TableRead objects (no type coercion)."""
    tables: list[TableRead] = []
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = [r for r in csv.reader(fh)]
        hdr = _detect_header(rows)
        cols = [_norm_header(c) for c in rows[hdr]]
        records = []
        for row in rows[hdr + 1 :]:
            if not any(_norm_header(v) for v in row):
                continue
            records.append({cols[j]: (v.strip() if isinstance(v, str) else v)
                            for j, v in enumerate(row) if j < len(cols)})
        tables.append(TableRead(path.name, None, hdr, cols, records, []))
    elif path.suffix.lower() in {".xlsx", ".xlsm"}:
        notes: list[str] = []
        try:
            excel = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
            raw_sheets: dict[str, list[list[Any]]] = {
                name: df.values.tolist() for name, df in excel.items()
            }
        except Exception as exc:  # openpyxl style-sheet crashes are common on portal exports
            notes.append(
                f"openpyxl failed ({type(exc).__name__}); parsed worksheet XML directly"
            )
            per_sheet: dict[str, list[list[Any]]] = {}
            for r_i, values in _iter_xlsx_rows(path):
                per_sheet.setdefault("_", []).append(values)
                break
            raw_sheets = {"Sheet1": per_sheet.get("_", [])}
            for r_i, values in _iter_xlsx_rows(path):
                raw_sheets["Sheet1"].append(values)
            raw_sheets["Sheet1"] = raw_sheets["Sheet1"][1:]
        for sheet_name, rows in raw_sheets.items():
            rows = [[None if (isinstance(v, float) and pd.isna(v)) else v for v in r]
                    for r in rows]
            hdr = _detect_header(rows)
            cols = [_norm_header(c) for c in rows[hdr]]
            records = []
            for row in rows[hdr + 1 :]:
                if not any(_norm_header(v) for v in row):
                    continue
                records.append({cols[j]: (str(v).strip() if v is not None else None)
                                for j, v in enumerate(row) if j < len(cols)})
            tables.append(TableRead(path.name, sheet_name, hdr, cols, records, notes))
    else:
        raise ValueError(f"Unsupported tabular source: {path}")
    return tables


RAW_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}


def discover_sources(raw_dir: Path) -> list[Path]:
    """Recursively find tabular source files under data/raw."""
    return sorted(
        p for p in raw_dir.rglob("*") if p.suffix.lower() in RAW_EXTENSIONS and p.is_file()
    )
