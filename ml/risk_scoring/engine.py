"""Step 9 — Unified risk scoring engine.

Combines four independently-computed components into a 0–100 member risk
score with LOW / MEDIUM / HIGH / CRITICAL bands. Component definitions:

* financial_risk      — hybrid of ensemble anomaly score and the actual
                        deviation magnitude from the entitlement benchmark
* data_quality_risk   — blank allocation cell + name hygiene defects
                        (these impede audit trail matching)
* duplicate_risk      — strongest potential-duplicate pair involving the
                        member
* interest_risk       — paise-level allocation components (interest-bearing
                        balances; smaller compliance-review signal)

Weights and band cut-offs are configurable (ml/config.py) and their
rationale is documented in docs/ml_methodology.md §5.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.config import RiskConfig

CRITICAL = "CRITICAL"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"


def _financial_risk(row: pd.Series) -> float:
    if bool(row["amount_missing"]):
        return 60.0  # cannot audit an amount that was never recorded
    dev = float(row["deviation_from_benchmark_pct"])
    if dev >= 50:
        deviation_component = 90.0
    elif dev >= 25:
        deviation_component = 70.0
    elif dev >= 10:
        deviation_component = 50.0
    elif dev >= 2:
        deviation_component = 30.0
    elif dev <= -25:
        deviation_component = 35.0   # possible pro-rated term — verify dates
    elif dev <= -2:
        deviation_component = 20.0
    else:
        deviation_component = 0.0
    ensemble_component = float(row["ensemble_score"]) * 60.0
    return round(min(100.0, max(deviation_component, ensemble_component)), 1)


def _data_quality_risk(row: pd.Series) -> float:
    score = 0.0
    if bool(row["amount_missing"]):
        score += 70.0
    if float(row["name_quality_score"]) < 0.7:
        score += 25.0
    elif float(row["name_quality_score"]) < 1.0:
        score += 12.0
    return round(min(100.0, score), 1)


def _duplicate_risk(max_pair_sim: float, flagged: bool) -> float:
    if flagged:
        return round(min(100.0, max_pair_sim * 100.0), 1)
    return round(min(100.0, max_pair_sim * 40.0), 1)


def _interest_risk(row: pd.Series) -> float:
    if float(row["paise_component"]) > 0:
        excess_cr = float(row.get("excess_over_benchmark_cr", 0.0))
        return round(min(100.0, 30.0 + excess_cr), 1)
    return 0.0


def risk_level(score: float, cfg: RiskConfig) -> str:
    for name, ceiling in cfg.levels:  # LOW <25, MEDIUM <45, HIGH <65
        if score < ceiling:
            return name
    return CRITICAL


_ESCALATION = {LOW: MEDIUM, MEDIUM: HIGH, HIGH: CRITICAL, CRITICAL: CRITICAL}


def _escalate(level: str, dup_flagged: bool, amount_missing: bool, cfg: RiskConfig) -> str:
    """Documented override: duplicate roster entry + unrecorded amount."""
    if cfg.escalate_duplicate_missing and dup_flagged and amount_missing:
        return _ESCALATION[level]
    return level


def compute_risk_scores(
    features: pd.DataFrame,
    anomaly: pd.DataFrame,
    duplicate_pairs: pd.DataFrame,
    cfg: RiskConfig,
) -> pd.DataFrame:
    base = anomaly.merge(
        features[["member_id", "name_quality_score", "excess_over_benchmark_cr"]],
        on="member_id",
    )

    dup_stats: dict[int, tuple[float, bool]] = {}
    if len(duplicate_pairs):
        for _, p in duplicate_pairs.iterrows():
            for mid, sim in (
                (int(p["member_id_a"]), float(p["overall_similarity"])),
                (int(p["member_id_b"]), float(p["overall_similarity"])),
            ):
                cur_sim, cur_flag = dup_stats.get(mid, (0.0, False))
                dup_stats[mid] = (max(cur_sim, sim), cur_flag or bool(p["potential_duplicate"]))

    rows = []
    for _, row in base.iterrows():
        max_sim, dup_flagged = dup_stats.get(int(row["member_id"]), (0.0, False))
        components = {
            "financial_risk": _financial_risk(row),
            "data_quality_risk": _data_quality_risk(row),
            "duplicate_risk": _duplicate_risk(max_sim, dup_flagged),
            "interest_risk": _interest_risk(row),
        }
        weights = {
            "financial_risk": cfg.financial_weight,
            "data_quality_risk": cfg.data_quality_weight,
            "duplicate_risk": cfg.duplicate_weight,
            "interest_risk": cfg.interest_weight,
        }
        total = sum(components[k] * weights[k] for k in components)
        level = risk_level(total, cfg)
        escalated_level = _escalate(level, dup_flagged, bool(row["amount_missing"]), cfg)
        rows.append(
            {
                "member_id": int(row["member_id"]),
                "risk_score": round(total, 1),
                "risk_level": escalated_level,
                "risk_escalated": escalated_level != level,
                "financial_risk": components["financial_risk"],
                "data_quality_risk": components["data_quality_risk"],
                "duplicate_risk": components["duplicate_risk"],
                "interest_risk": components["interest_risk"],
                "max_duplicate_similarity": round(max_sim, 4),
                "flagged_duplicate_pair": dup_flagged,
            }
        )
    return pd.DataFrame(rows)
