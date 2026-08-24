"""Step 4 — Feature engineering.

Builds the per-member analytical feature matrix from the cleaned allocation
table. Features are exclusively derived from columns that exist in the
source dataset; the empirical modal allocation (₹14.7 crore, held by ~72%
of members) serves as the *full-entitlement benchmark*.

Leakage policy: the cleaned table contains no outcome/label columns, so no
supervised leakage is possible. Anomaly scores produced downstream are never
fed back into features.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_VERSION = "v1"

# Columns fed to the anomaly detectors (missing amounts are imputed to the
# benchmark with an indicator column so detectors can use the missingness
# signal itself).
MODEL_FEATURES = [
    "benchmark_ratio",
    "log_amount",
    "excess_over_benchmark_cr",
    "shortfall_ratio",
    "paise_component",
    "state_deviation_pct",
    "state_percentile",
    "amount_missing_ind",
    "name_quality_score",
]


def empirical_benchmark(amounts: pd.Series) -> float:
    """The modal allocation across all members — the de-facto full-entitlement
    benchmark for the current Lok Sabha tranche (data-driven, not assumed)."""
    mode = amounts.mode()
    if mode.empty:
        raise ValueError("Cannot compute empirical benchmark from empty series")
    return float(mode.iloc[0])


def name_quality_score(row: pd.Series) -> float:
    """0–1 cleanliness score for the stored member name (1 = clean).

    Penalises title prefixes, ALL-CAPS/all-lower casing and doubled spaces —
    all observed in the source file and all relevant to record matching.
    """
    score = 1.0
    if bool(row["has_title_prefix"]):
        score -= 0.15
    if not bool(row["name_case_consistent"]):
        score -= 0.25
    if bool(row["name_has_double_space"]):
        score -= 0.10
    return round(max(score, 0.0), 3)


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return (features DataFrame indexed by member_id, feature metadata)."""
    out = df[["member_id", "sr_no", "state", "mp_name", "mp_name_clean",
              "constituency", "constituency_base", "constituency_category",
              "allocated_amount", "amount_missing", "amount_has_paise"]].copy()

    benchmark = empirical_benchmark(df["allocated_amount"])
    out["benchmark_amount"] = benchmark

    amt = out["allocated_amount"]
    out["benchmark_ratio"] = (amt / benchmark).where(amt.notna())
    out["log_amount"] = pd.Series(
        np.log10(amt.astype(float).to_numpy()), index=amt.index
    ).where(amt.notna())
    out["excess_over_benchmark_cr"] = ((amt - benchmark).clip(lower=0) / 1e7).where(amt.notna())
    out["shortfall_ratio"] = ((benchmark - amt).clip(lower=0) / benchmark).where(amt.notna())
    out["paise_component"] = (amt % 1 * 100).where(amt.notna(), 0.0).round(2)

    # Peer statistics: state-level median/mean and member's position in state
    state_median = df.groupby("state")["allocated_amount"].transform("median")
    out["state_median_amount"] = state_median
    out["state_deviation_pct"] = ((amt - state_median) / state_median).where(amt.notna())
    out["state_percentile"] = df.groupby("state")["allocated_amount"].rank(pct=True).where(amt.notna())
    out["national_percentile"] = amt.rank(pct=True).where(amt.notna())

    out["is_above_benchmark"] = (out["benchmark_ratio"] > 1.0001).fillna(False)
    out["is_below_benchmark"] = (out["benchmark_ratio"] < 0.9999).fillna(False)

    out["name_quality_score"] = df.apply(name_quality_score, axis=1)

    # Imputations for the detectors (indicators keep the signal explicit)
    out["amount_missing_ind"] = out["amount_missing"].astype(float)
    for col in ("benchmark_ratio", "log_amount", "state_deviation_pct", "state_percentile"):
        out[col] = out[col].fillna(
            {"benchmark_ratio": 1.0, "log_amount": np.log10(benchmark),
             "state_deviation_pct": 0.0, "state_percentile": 0.5}[col]
        )
    out["excess_over_benchmark_cr"] = out["excess_over_benchmark_cr"].fillna(0.0)
    out["shortfall_ratio"] = out["shortfall_ratio"].fillna(0.0)

    metadata = {
        "feature_version": FEATURE_VERSION,
        "benchmark_amount": benchmark,
        "model_features": MODEL_FEATURES,
        "imputation_policy": (
            "missing amounts imputed to the empirical benchmark ratio=1.0 "
            "with an explicit amount_missing indicator"
        ),
        "feature_definitions": {
            "benchmark_ratio": "allocated_amount / empirical modal allocation",
            "log_amount": "log10(allocated_amount)",
            "excess_over_benchmark_cr": "max(amount − benchmark, 0) in ₹ crore",
            "shortfall_ratio": "max(benchmark − amount, 0) / benchmark",
            "paise_component": "sub-rupee (paise) part of the allocation",
            "state_deviation_pct": "(amount − state median) / state median",
            "state_percentile": "percentile rank of amount within state",
            "amount_missing_ind": "1 when the allocation cell is blank in source",
            "name_quality_score": "0–1 name cleanliness (titles/casing/spacing)",
        },
    }
    return out, metadata
