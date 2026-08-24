"""Step 5 — Financial anomaly detection.

Three independent detectors are run on the feature matrix and compared:

1. Statistical — Iglewicz & Hoaglin robust z-score (MAD-based) on the
   benchmark ratio. Robust to the extreme right tail in this distribution.
2. Isolation Forest — multivariate, captures members unusual in *combinations*
   (e.g. slightly-above allocation + large paise component).
3. Local Outlier Factor — density-based, finds members unusual relative to
   their local neighbourhood even when globally unremarkable.

Each detector returns a risk-oriented score in [0, 1] (1 = most anomalous)
and a boolean flag at its configured threshold. The ensemble requires
``ensemble_vote_threshold`` agreeing flags (or a normalised ensemble score
≥ ``ensemble_score_threshold``).

All thresholds live in ml/config.py and are environment-overridable.
No label exists in the source data; detection is fully unsupervised and
findings are investigative leads, never fraud verdicts.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler

from ml.config import AnomalyConfig
from ml.features.engineer import MODEL_FEATURES

METHODS = ("robust_z", "isolation_forest", "lof")


@dataclass
class DetectorResult:
    method: str
    score: np.ndarray          # risk-oriented, 0..1 (higher = more anomalous)
    flagged: np.ndarray        # boolean per member
    threshold: float           # the flag rule, for transparency in the UI
    detail: dict


def _minmax_risk(values: np.ndarray) -> np.ndarray:
    """Map raw abnormality values to [0,1] with 1 = most abnormal."""
    v = np.asarray(values, dtype=float)
    lo, hi = np.nanmin(v), np.nanmax(v)
    if np.isclose(lo, hi):
        return np.zeros_like(v)
    return (v - lo) / (hi - lo)


def robust_z_detector(ratio: np.ndarray, cfg: AnomalyConfig) -> DetectorResult:
    """MAD-based robust z-score (Iglewicz & Hoaglin, ±3.5 rule)."""
    med = np.nanmedian(ratio)
    mad = np.nanmedian(np.abs(ratio - med))
    if mad == 0:
        # Degenerate case: >50% of values identical → any deviation is unusual.
        # Use a small epsilon tied to measurement scale (₹1 / benchmark).
        mad = 1.0 / 147_000_000.0
    z = 0.6745 * (ratio - med) / mad
    score = _minmax_risk(np.abs(z))
    flagged = np.abs(z) > cfg.robust_z_threshold
    return DetectorResult(
        method="robust_z",
        score=score,
        flagged=flagged,
        threshold=cfg.robust_z_threshold,
        detail={"median_ratio": float(med), "mad": float(mad)},
    )


def isolation_forest_detector(X: np.ndarray, cfg: AnomalyConfig) -> DetectorResult:
    iforest = IsolationForest(
        n_estimators=cfg.isolation_forest_n_estimators,
        contamination=cfg.contamination,
        random_state=cfg.isolation_forest_random_state,
        n_jobs=-1,
    )
    labels = iforest.fit_predict(X)  # -1 anomaly, 1 normal
    scores_raw = -iforest.score_samples(X)  # higher = more abnormal
    score = _minmax_risk(scores_raw)
    flagged = labels == -1
    return DetectorResult(
        method="isolation_forest",
        score=score,
        flagged=flagged,
        threshold=cfg.contamination,
        detail={"n_estimators": cfg.isolation_forest_n_estimators,
                "random_state": cfg.isolation_forest_random_state},
    )


def lof_detector(X: np.ndarray, cfg: AnomalyConfig) -> DetectorResult:
    lof = LocalOutlierFactor(n_neighbors=cfg.lof_n_neighbors, contamination=cfg.contamination)
    labels = lof.fit_predict(X)
    scores_raw = -lof.negative_outlier_factor_  # higher = more abnormal
    score = _minmax_risk(scores_raw)
    flagged = labels == -1
    return DetectorResult(
        method="lof",
        score=score,
        flagged=flagged,
        threshold=cfg.contamination,
        detail={"n_neighbors": cfg.lof_n_neighbors},
    )


def run_anomaly_detection(
    features: pd.DataFrame, cfg: AnomalyConfig
) -> tuple[pd.DataFrame, dict]:
    """Run all detectors + ensemble. Returns per-member scores and comparison."""
    X_df = features[MODEL_FEATURES].astype(float)
    X = RobustScaler().fit_transform(X_df)

    results: dict[str, DetectorResult] = {
        "robust_z": robust_z_detector(features["benchmark_ratio"].to_numpy(float), cfg),
        "isolation_forest": isolation_forest_detector(X, cfg),
        "lof": lof_detector(X, cfg),
    }

    out = features[["member_id"]].copy()
    for name, res in results.items():
        out[f"score_{name}"] = res.score.round(4)
        out[f"flag_{name}"] = res.flagged

    votes = np.column_stack([results[m].flagged for m in METHODS]).sum(axis=1)
    ensemble_score = np.column_stack([results[m].score for m in METHODS]).mean(axis=1)
    ensemble_flag = (votes >= cfg.ensemble_vote_threshold) | (
        ensemble_score >= cfg.ensemble_score_threshold
    )
    out["anomaly_votes"] = votes
    out["ensemble_score"] = ensemble_score.round(4)
    out["is_anomaly"] = ensemble_flag

    def reasons(row: pd.Series) -> list[str]:
        recs: list[str] = []
        if bool(row.get("amount_missing", False)):
            recs.append("Allocation amount is blank in the source record")
        if bool(row.get("is_above_benchmark", False)):
            dev = float(row["deviation_from_benchmark_pct"])
            if dev > 25:
                recs.append(
                    f"Allocation is {dev:.0f}% above the ₹{row['benchmark_amount']/1e7:.1f} cr "
                    "full-entitlement benchmark"
                )
        if bool(row.get("is_below_benchmark", False)):
            recs.append(
                f"Allocation is {abs(float(row['deviation_from_benchmark_pct'])):.0f}% below "
                "the full-entitlement benchmark (possible pro-rated term — verify membership dates)"
            )
        if float(row.get("paise_component", 0)) > 0:
            recs.append(
                f"Non-round allocation (₹{float(row['paise_component']):.2f} paise component) "
                "suggests interest-bearing balance accrual"
            )
        if int(row.get("anomaly_votes", 0)) >= 2:
            recs.append(
                f"{int(row['anomaly_votes'])}/3 anomaly methods agree "
                f"(ensemble score {float(row['ensemble_score']):.2f})"
            )
        return recs

    merged = out.merge(
        features[["member_id", "amount_missing", "is_above_benchmark",
                  "is_below_benchmark", "paise_component", "deviation_from_benchmark_pct",
                  "benchmark_amount", "state_deviation_pct"]],
        on="member_id",
    )
    merged["anomaly_reasons"] = merged.apply(reasons, axis=1)

    comparison = {
        "methods": {
            m: {
                "flagged_count": int(results[m].flagged.sum()),
                "threshold": results[m].threshold,
                "detail": results[m].detail,
            }
            for m in METHODS
        },
        "ensemble": {
            "flagged_count": int(ensemble_flag.sum()),
            "vote_threshold": cfg.ensemble_vote_threshold,
            "score_threshold": cfg.ensemble_score_threshold,
            "flagged_pct": round(100.0 * ensemble_flag.mean(), 2),
        },
    }
    return merged, comparison
