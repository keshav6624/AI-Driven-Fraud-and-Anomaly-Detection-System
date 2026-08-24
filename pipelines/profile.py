"""Step 1 — Dataset discovery & profiling.

Scans data/raw, profiles every tabular file (shape, dtypes, missingness,
uniqueness, duplicates, numeric distributions, categorical distributions),
detects likely identifiers/keys, flags potential leakage variables, and
writes a machine-readable + human-readable profiling report to
data/profiling/.

No modelling happens here. The report is the contract for everything
downstream.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pipelines.sources import TableRead, discover_sources, read_table

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROFILING_DIR = ROOT / "data" / "profiling"

TRAILER_MARKERS = {"grand total", "total", "subtotal", "summary"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_trailer(rec: dict[str, Any]) -> bool:
    first = str(next(iter(rec.values()), "")).strip().lower()
    return any(first == m or first.startswith(m) for m in TRAILER_MARKERS)


def _coerce_numeric(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        cleaned = (
            series.astype(str)
            .str.replace(r"[₹,\s]", "", regex=True)
            .replace({"nan": None, "None": None, "": None})
        )
        return pd.to_numeric(cleaned, errors="coerce")
    return pd.to_numeric(series, errors="coerce")


def _percentile_summary(values: np.ndarray) -> dict[str, float]:
    if len(values) == 0:
        return {}
    return {
        "min": float(np.min(values)),
        "p01": float(np.percentile(values, 1)),
        "p05": float(np.percentile(values, 5)),
        "p25": float(np.percentile(values, 25)),
        "median": float(np.median(values)),
        "p75": float(np.percentile(values, 75)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
    }


def profile_column(df: pd.DataFrame, col: str) -> dict[str, Any]:
    series = df[col]
    n = len(series)
    non_null = series.notna().sum()
    profile: dict[str, Any] = {
        "column": col,
        "dtype": str(series.dtype),
        "non_null": int(non_null),
        "missing": int(n - non_null),
        "missing_pct": round(100.0 * (n - non_null) / n, 3) if n else 0.0,
        "unique": int(series.nunique(dropna=True)),
        "unique_pct": round(100.0 * series.nunique(dropna=True) / n, 3) if n else 0.0,
    }
    numeric = _coerce_numeric(series)
    numeric_valid = numeric.dropna()
    # A column is treated as numeric if coercion succeeds on >=95% of non-null values
    if non_null and len(numeric_valid) / non_null >= 0.95 and series.nunique(dropna=True) > 2:
        profile["role"] = "numeric"
        profile["distribution"] = _percentile_summary(numeric_valid.to_numpy())
        profile["mode_value"] = float(numeric_valid.mode().iloc[0]) if len(numeric_valid) else None
        profile["mode_share_pct"] = round(
            100.0 * (numeric_valid == numeric_valid.mode().iloc[0]).mean(), 2
        ) if len(numeric_valid) else 0.0
        profile["zero_count"] = int((numeric_valid == 0).sum())
    else:
        profile["role"] = "categorical"
        top = series.value_counts(dropna=True).head(12)
        profile["top_values"] = {str(k): int(v) for k, v in top.items()}
        profile["whitespace_issues"] = int(
            series.dropna().astype(str).str.contains(r"\s{2,}|^\s|\s$", regex=True).sum()
        )
        # ratio columns that look numeric but are actually identifiers
        if profile["unique_pct"] and profile["unique_pct"] > 95:
            profile["likely_role"] = "identifier"
    return profile


def infer_keys_and_relations(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive candidate primary keys and joinable columns across tables."""
    findings: list[dict[str, Any]] = []
    for prof in profiles:
        key_cols = [
            c for c in prof["columns"] if c.get("likely_role") == "identifier"
        ]
        cat_cols = [
            c["column"] for c in prof["columns"] if c.get("role") == "categorical"
        ]
        findings.append(
            {
                "file": prof["file"],
                "table": prof["table"],
                "row_count": prof["rows_excluding_trailers"],
                "candidate_primary_keys": key_cols or cat_cols[:1],
                "high_cardinality_categoricals": cat_cols[:5],
                "grain": "one row per member of parliament (Sr. No. unique)"
                if any(c["column"] == "Sr. No." for c in prof["columns"])
                else "unknown — inspect manually",
            }
        )
    return findings


def flag_leakage_candidates(prof: dict[str, Any]) -> list[str]:
    """Columns that must never be used as model inputs because they are
    outcomes/labels or direct derivatives of the prediction target."""
    flags: list[str] = []
    for c in prof["columns"]:
        name = c["column"].lower()
        if any(tok in name for tok in ("fraud", "label", "target", "flagged", "verified")):
            flags.append(c["column"])
    return flags


def profile_dataset() -> dict[str, Any]:
    files = discover_sources(RAW_DIR)
    if not files:
        raise SystemExit(f"No tabular source files found under {RAW_DIR}")

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_directory": str(RAW_DIR),
        "files": [],
        "cross_file_relationships": [],
        "global_notes": [],
    }
    table_profiles: list[dict[str, Any]] = []

    for path in files:
        tables: list[TableRead] = read_table(path)
        for t in tables:
            records = [r for r in t.records if not _is_trailer(r)]
            trailers = [r for r in t.records if _is_trailer(r)]
            df = pd.DataFrame(records)
            # exact duplicate records (all columns equal)
            dup_count = int(df.duplicated().sum()) if len(df) else 0
            prof: dict[str, Any] = {
                "file": t.file_name,
                "table": t.sheet_name or path.stem,
                "sha256": _sha256(path),
                "rows_raw": len(t.records),
                "rows_excluding_trailers": len(records),
                "trailer_rows": len(trailers),
                "duplicate_records": dup_count,
                "column_count": len(df.columns),
                "header_row_index": t.header_row_index,
                "parser_notes": t.notes,
                "trailer_values": [
                    {k: v for k, v in r.items() if v not in (None, "", " ")}
                    for r in trailers
                ],
                "columns": [profile_column(df, c) for c in df.columns],
            }
            prof["leakage_candidates"] = flag_leakage_candidates(prof)
            table_profiles.append(prof)

    report["tables"] = table_profiles
    report["cross_file_relationships"] = infer_keys_and_relations(table_profiles)
    report["global_notes"].extend(
        [
            "Single-table dataset: one row per Hon'ble MP with the MPLADS allocated "
            "amount. No project-level, transaction-level, date, expenditure or "
            "physical-progress fields exist in the provided sources.",
            "Post-hoc derivation policy: every derived metric used downstream must "
            "be traceable to these columns; missing information is documented, "
            "never fabricated (see docs/ml_methodology.md).",
        ]
    )
    return report


def _markdown(report: dict[str, Any]) -> str:
    lines = ["# MPLAD-Sentinel — Dataset Profiling Report", ""]
    lines.append(f"_Generated: {report['generated_at']}_")
    lines.append("")
    for t in report["tables"]:
        lines += [
            f"## {t['file']}" + (f" — sheet `{t['table']}`" if t["table"] != t["file"] else ""),
            "",
            f"- SHA-256: `{t['sha256']}`",
            f"- Rows (raw / excl. trailers / duplicates): {t['rows_raw']} / "
            f"{t['rows_excluding_trailers']} / {t['duplicate_records']}",
            f"- Columns: {t['column_count']}",
        ]
        if t["parser_notes"]:
            lines.append(f"- Parser notes: {'; '.join(t['parser_notes'])}")
        lines += ["", "| Column | Role | Missing % | Unique | Mode / Top value |", "|---|---|---|---|---|"]
        for c in t["columns"]:
            if c.get("role") == "numeric":
                mode = f"{c.get('mode_value'):,.0f} ({c.get('mode_share_pct')}% of rows)"
            else:
                top = c.get("top_values") or {}
                first = next(iter(top.items()), ("—", 0))
                mode = f"{first[0]} ({first[1]})"
            lines.append(
                f"| {c['column']} | {c.get('role', '?')}"
                f"{' (identifier-like)' if c.get('likely_role') == 'identifier' else ''} "
                f"| {c['missing_pct']}% | {c['unique']} | {mode} |"
            )
        lines.append("")
        if t["trailer_values"]:
            lines.append("**Trailer (grand-total) row detected** (excluded from analysis, "
                         "retained as a checksum): " + json.dumps(t["trailer_values"], ensure_ascii=False))
            lines.append("")
    lines += ["## Relationships / keys", ""]
    for rel in report["cross_file_relationships"]:
        lines.append(f"- `{rel['file']}`: grain = {rel['grain']}; candidate PK = "
                     f"{rel['candidate_primary_keys']}")
    lines += ["", "## Notes", ""]
    lines += [f"- {n}" for n in report["global_notes"]]
    return "\n".join(lines)


def main() -> None:
    PROFILING_DIR.mkdir(parents=True, exist_ok=True)
    report = profile_dataset()
    out_json = PROFILING_DIR / "dataset_profile.json"
    out_md = PROFILING_DIR / "dataset_profile.md"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    out_md.write_text(_markdown(report), encoding="utf-8")
    print(f"[profile] wrote {out_json}")
    print(f"[profile] wrote {out_md}")
    for t in report["tables"]:
        print(f"  - {t['file']}: {t['rows_excluding_trailers']} rows x {t['column_count']} cols, "
              f"{t['duplicate_records']} exact duplicates")


if __name__ == "__main__":
    main()
