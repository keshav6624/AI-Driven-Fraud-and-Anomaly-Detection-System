"""Step 10 — Explainability.

Two complementary explanation layers, both computed from actual data:

1. Component decomposition — each risk component's weighted contribution
   (in points of the 0–100 score) with the supporting metric that drove it.
2. Leave-one-feature-out (LOFO) attribution of the Isolation Forest — for
   every ensemble-flagged member, the model is re-scored with one feature
   removed at a time; the drop in the member's abnormality score is that
   feature's contribution. This is exact for tree ensembles on small data
   (543 members re-fit 9 times runs in <2 s) and is fully traceable.

SHAP is not used because there is no supervised model in this dataset
(no outcome labels exist to train on); that gap is documented in
docs/ml_methodology.md §6 and ml/delay_prediction/capability.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from ml.config import MLConfig
from ml.features.engineer import MODEL_FEATURES


def _lofo_attributions(
    features: pd.DataFrame, cfg: MLConfig
) -> dict[int, dict[str, float]]:
    """Per-member {feature: contribution to Isolation Forest abnormality}."""
    def fit_scores(X: np.ndarray) -> np.ndarray:
        iforest = IsolationForest(
            n_estimators=cfg.anomaly.isolation_forest_n_estimators,
            contamination=cfg.anomaly.contamination,
            random_state=cfg.anomaly.isolation_forest_random_state,
            n_jobs=-1,
        )
        iforest.fit(X)
        raw = -iforest.score_samples(X)
        lo, hi = raw.min(), raw.max()
        return (raw - lo) / (hi - lo) if hi > lo else raw * 0

    X_full = RobustScaler().fit_transform(features[MODEL_FEATURES].astype(float))
    full_scores = fit_scores(X_full)

    per_feature_drop: dict[str, np.ndarray] = {}
    for feat in MODEL_FEATURES:
        cols = [c for c in MODEL_FEATURES if c != feat]
        X_sub = RobustScaler().fit_transform(features[cols].astype(float))
        sub_scores = fit_scores(X_sub)
        per_feature_drop[feat] = full_scores - sub_scores  # +ve = feat increased abnormality

    out: dict[int, dict[str, float]] = {}
    for _, row in features.iterrows():
        mid = int(row["member_id"])
        if mid not in _flagged_ids:
            continue
        out[mid] = {
            feat: round(float(drop[int(row.name)]), 4)
            for feat, drop in per_feature_drop.items()
        }
    return out


# module-level set of member ids flagged by the ensemble; set by explain()
_flagged_ids: set[int] = set()


def explain(
    features: pd.DataFrame,
    anomaly: pd.DataFrame,
    risk: pd.DataFrame,
    cfg: MLConfig,
) -> pd.DataFrame:
    global _flagged_ids
    merged = (
        risk.merge(anomaly[["member_id", "anomaly_reasons", "ensemble_score", "anomaly_votes"]],
                   on="member_id")
        .merge(features[["member_id", "state", "mp_name", "constituency",
                         "allocated_amount", "benchmark_amount",
                         "deviation_from_benchmark_pct", "paise_component",
                         "amount_missing", "name_quality_score"]],
               on="member_id")
    )
    _flagged_ids = set(merged.loc[merged["financial_risk"] >= 50, "member_id"])
    _flagged_ids |= set(merged.loc[merged["risk_score"] >= 55, "member_id"])

    lofo = _lofo_attributions(features.reset_index(drop=True), cfg)

    weights = {
        "financial_risk": cfg.risk.financial_weight,
        "data_quality_risk": cfg.risk.data_quality_weight,
        "duplicate_risk": cfg.risk.duplicate_weight,
        "interest_risk": cfg.risk.interest_weight,
    }

    def factors(row: pd.Series) -> list[dict]:
        comps = {
            "Financial": row["financial_risk"],
            "Data quality": row["data_quality_risk"],
            "Duplicate": row["duplicate_risk"],
            "Interest/rounding": row["interest_risk"],
        }
        out = []
        if bool(row["amount_missing"]):
            out.append({
                "factor": "Allocation amount not recorded",
                "contribution_points": round(row["data_quality_risk"] * weights["data_quality_risk"], 1),
                "support": "Source cell for allocated amount is blank",
            })
        dev = float(row["deviation_from_benchmark_pct"])
        if abs(dev) >= 2:
            out.append({
                "factor": f"Allocation {abs(dev):.0f}% "
                          f"{'above' if dev > 0 else 'below'} entitlement benchmark",
                "contribution_points": round(row["financial_risk"] * weights["financial_risk"], 1),
                "support": f"₹{float(row['allocated_amount'])/1e7:,.2f} cr vs benchmark "
                           f"₹{float(row['benchmark_amount'])/1e7:.1f} cr "
                           f"({int(row['anomaly_votes'])}/3 methods agree)",
            })
        elif row["ensemble_score"] >= 0.6:
            out.append({
                "factor": "Unusual multivariate pattern",
                "contribution_points": round(row["financial_risk"] * weights["financial_risk"], 1),
                "support": f"ensemble anomaly score {float(row['ensemble_score']):.2f} "
                           "from combined allocation/interest/peer features",
            })
        if bool(row.get("flagged_duplicate_pair", False)):
            out.append({
                "factor": "Potential duplicate member record",
                "contribution_points": round(row["duplicate_risk"] * weights["duplicate_risk"], 1),
                "support": f"similar record similarity "
                           f"{float(row['max_duplicate_similarity']):.2f} — REQUIRES VERIFICATION",
            })
        if float(row["paise_component"]) > 0:
            out.append({
                "factor": "Non-round allocation (interest component)",
                "contribution_points": round(row["interest_risk"] * weights["interest_risk"], 1),
                "support": f"₹{float(row['paise_component']):.2f} paise part implies "
                           "interest-bearing balance accrual",
            })
        if float(row["name_quality_score"]) < 0.7:
            out.append({
                "factor": "Member name formatting defects",
                "contribution_points": round(row["data_quality_risk"] * weights["data_quality_risk"], 1),
                "support": f"name hygiene score {float(row['name_quality_score']):.2f} "
                           "(title prefixes / casing / spacing hinder record matching)",
            })
        out.sort(key=lambda f: f["contribution_points"], reverse=True)
        return out

    def actions(row: pd.Series) -> list[str]:
        recs = []
        if bool(row["amount_missing"]):
            recs.append("Obtain the missing allocation figure from MoSPI records and correct the register")
        dev = float(row["deviation_from_benchmark_pct"])
        if dev >= 25:
            recs.append("Review sanction ledger for carry-forward/unspent balances explaining the excess")
        if dev <= -25:
            recs.append("Verify membership start date (by-election / replaced member) to confirm pro-rating")
        if bool(row.get("flagged_duplicate_pair", False)):
            recs.append("Cross-check the matched record — confirm whether two roster entries exist in error")
        if float(row["paise_component"]) > 0:
            recs.append("Reconcile interest accrual on unspent balance with agency bank statements")
        if not recs:
            recs.append("No investigative action indicated by current signals")
        return recs

    merged["risk_factors"] = merged.apply(factors, axis=1)
    merged["recommended_actions"] = merged.apply(actions, axis=1)
    merged["lofo_attribution"] = merged["member_id"].map(
        lambda mid: lofo.get(int(mid), {})
    )
    return merged
