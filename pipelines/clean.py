"""Step 2 — Cleaning.

Raw data is never modified. This stage reads data/raw, produces a typed,
normalized table in data/processed, preserves original values in
``*_raw`` columns, and emits a data-quality validation report.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from pipelines.sources import read_table

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PROFILING_DIR = ROOT / "data" / "profiling"

# Canonical column names for the MP entitlement allocation table
CANONICAL_COLUMNS = {
    "sr_no": ["sr. no.", "srno", "s no", "s.no"],
    "state": ["state"],
    "mp_name": ["hon'ble members of parliaments", "mp name", "member name"],
    "constituency": ["constituency"],
    "allocated_amount": ["allocated amount ( ₹ )", "allocated amount", "allocated_amount"],
}

TITLE_PREFIXES = [
    "Shri", "Smt", "Dr.", "Dr", "Adv.", "Adv", "Mr.", "Mr", "Ms.", "Ms",
    "Mrs.", "Mrs", "Prof.", "Prof", "Capt.", "Captain", "Swami", "Maharaj",
]
HONORIFIC_RE = re.compile(
    r"^(?:" + "|".join(re.escape(t) for t in TITLE_PREFIXES) + r")\s+",
    flags=re.IGNORECASE,
)


def _map_columns(cols: list[str]) -> dict[str, str]:
    """Map raw header names to canonical names using the alias table."""
    norm = {c.strip().lower(): c for c in cols}
    mapping: dict[str, str] = {}
    for canon, aliases in CANONICAL_COLUMNS.items():
        for alias in aliases:
            if alias in norm:
                mapping[canon] = norm[alias]
                break
        else:
            # fall back to fuzzy contains
            for lower, raw in norm.items():
                if canon in lower.replace("(", " ").replace(")", " "):
                    mapping[canon] = raw
                    break
    return mapping


def _strip_titles(name: str) -> str:
    prev = None
    out = name
    while prev != out:
        prev = out
        out = HONORIFIC_RE.sub("", out)
    return out


def _has_title_prefix(name: str) -> bool:
    return bool(HONORIFIC_RE.match(name.strip()))


def _name_case_consistent(name: str) -> bool:
    """Detect ALL-CAPS or all-lowercase names (formatting inconsistency)."""
    letters = [c for c in name if c.isalpha()]
    if not letters:
        return True
    return not (all(c.isupper() for c in letters) or all(c.islower() for c in letters))


def clean_allocations() -> tuple[pd.DataFrame, dict]:
    """Produce the cleaned MP allocation table and its quality report."""
    src = next(p for p in sorted(RAW_DIR.rglob("*.xlsx")) if p.is_file())
    table = read_table(src)[0]

    records = [r for r in table.records if not str(r.get("Sr. No.", "")).lower().startswith("grand")]
    trailer = [
        r for r in table.records if str(r.get("Sr. No.", "")).lower().startswith("grand")
    ]
    raw = pd.DataFrame(records)
    raw.columns = [c.strip() for c in raw.columns]

    colmap = _map_columns(list(raw.columns))
    missing_canonical = [c for c in CANONICAL_COLUMNS if c not in colmap]
    if missing_canonical:
        raise ValueError(f"Source is missing expected columns: {missing_canonical} (found {list(raw.columns)})")

    df = pd.DataFrame()
    df["sr_no"] = pd.to_numeric(raw[colmap["sr_no"]], errors="coerce").astype("Int64")
    df["state_raw"] = raw[colmap["state"]].astype("string").str.strip()
    df["mp_name_raw"] = raw[colmap["mp_name"]].astype("string").str.strip()
    df["constituency_raw"] = raw[colmap["constituency"]].astype("string").str.strip()

    amt_str = (
        raw[colmap["allocated_amount"]].astype("string")
        .str.replace(r"[₹,\s]", "", regex=True)
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )
    df["allocated_amount"] = pd.to_numeric(amt_str, errors="coerce")
    df["allocated_amount_raw"] = raw[colmap["allocated_amount"]].astype("string")

    # exact duplicates on the business key (state, mp name, constituency)
    key = ["state_raw", "mp_name_raw", "constituency_raw"]
    dup_mask = df.duplicated(subset=key, keep=False)

    # normalized fields (originals preserved above)
    df["state"] = df["state_raw"].str.replace(r"\s+", " ", regex=True)
    df["mp_name"] = df["mp_name_raw"].str.replace(r"\s+", " ", regex=True)
    df["mp_name_clean"] = (
        df["mp_name"].map(_strip_titles).str.replace(r"\s+", " ", regex=True).str.strip()
    )
    df["has_title_prefix"] = df["mp_name"].map(_has_title_prefix)
    df["name_case_consistent"] = df["mp_name_clean"].map(_name_case_consistent)
    df["name_has_double_space"] = df["mp_name_raw"].str.contains(r"\s{2,}", regex=True)
    df["constituency"] = df["constituency_raw"].str.replace(r"\s+", " ", regex=True)
    df["amount_missing"] = df["allocated_amount"].isna()
    df["amount_has_paise"] = (df["allocated_amount"] % 1).fillna(0) > 0

    # constituency reserved-category marker, e.g. "AURANGABAD_BR" keeps its suffix
    df["constituency_category"] = np.where(
        df["constituency"].str.contains(r"\(SC\)|\(ST\)", regex=True),
        df["constituency"].str.extract(r"\((SC|ST)\)", expand=False).str.lower(),
        "general",
    )
    df["constituency_base"] = (
        df["constituency"].str.replace(r"\s*\((SC|ST)\)", "", regex=True)
        .str.replace(r"_([A-Z]{2})$", r" (\1)", regex=True)
    )

    # stable surrogate member id from the business key
    df["member_key"] = (
        df["state"].str.lower() + "|" + df["mp_name_clean"].str.lower() + "|" + df["constituency"].str.lower()
    )

    df = df.sort_values("sr_no").reset_index(drop=True)
    df.insert(0, "member_id", np.arange(1, len(df) + 1))

    # ---- validation report -------------------------------------------------
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    check("row_count_is_543", len(df) == 543, f"rows={len(df)} (Lok Sabha strength)")
    check("sr_no_unique", df["sr_no"].is_unique, f"unique={df['sr_no'].nunique()}")
    check("no_exact_duplicate_records", int(dup_mask.sum()) == 0,
          f"exact business-key duplicates={int(dup_mask.sum())}")
    check("no_missing_state", int(df["state"].isna().sum()) == 0, "state never null")
    check("no_missing_mp_name", int(df["mp_name"].isna().sum()) == 0, "mp name never null")
    check("no_missing_constituency", int(df["constituency"].isna().sum()) == 0,
          "constituency never null")
    check("states_all_valid", df["state"].str.len().min() > 2,
          f"{df['state'].nunique()} distinct states/UTs")
    check("amounts_positive_where_present",
          bool((df["allocated_amount"].dropna() > 0).all()),
          f"min={df['allocated_amount'].min()}")
    check("amount_within_reasonable_bound",
          bool(df["allocated_amount"].max() <= 600_000_000),
          f"max={df['allocated_amount'].max():,.2f} (bound=₹60 cr)")

    if trailer:
        stated = float(trailer[0].get("Allocated AMOUNT ( ₹ )"))
        computed = float(df["allocated_amount"].sum())
        check("grand_total_matches_column_sum", abs(stated - computed) < 0.01,
              f"stated={stated:,.2f} computed={computed:,.2f}")
    else:
        check("grand_total_matches_column_sum", False, "no trailer row found")

    quality = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": src.name,
        "rows": len(df),
        "checks": checks,
        "failed_checks": [c["check"] for c in checks if not c["passed"]],
        "data_quality_flags": {
            "missing_allocation_amount": int(df["amount_missing"].sum()),
            "amounts_with_paise_component": int(df["amount_has_paise"].sum()),
            "names_with_title_prefix": int(df["has_title_prefix"].sum()),
            "names_all_caps_or_lower": int((~df["name_case_consistent"]).sum()),
            "names_with_double_spaces": int(df["name_has_double_space"].sum()),
            "shared_constituency_names": int(
                df.duplicated(subset=["constituency"], keep=False).sum()
            ),
        },
    }
    return df, quality


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    PROFILING_DIR.mkdir(parents=True, exist_ok=True)
    df, quality = clean_allocations()
    df.to_csv(PROCESSED_DIR / "mp_allocations_clean.csv", index=False)
    (PROFILING_DIR / "data_quality_report.json").write_text(
        json.dumps(quality, indent=2, default=str), encoding="utf-8"
    )
    print(f"[clean] wrote {PROCESSED_DIR/'mp_allocations_clean.csv'} ({len(df)} rows)")
    print(f"[clean] checks passed: {sum(c['passed'] for c in quality['checks'])}/{len(quality['checks'])}")
    for c in quality["checks"]:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"  [{status}] {c['check']}: {c['detail']}")
    print("[clean] data-quality flags:", json.dumps(quality["data_quality_flags"]))


if __name__ == "__main__":
    main()
