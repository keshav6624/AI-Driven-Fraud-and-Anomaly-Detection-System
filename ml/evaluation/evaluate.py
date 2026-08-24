"""Step 19 — Model evaluation.

With no ground-truth labels in the source data, anomaly detection is
unsupervised; this module evaluates it the honest way:

* distribution of ensemble scores and flag counts per method;
* pairwise method agreement (Jaccard of flag sets, Spearman correlation of
  continuous scores);
* threshold stability — flag counts and agreement when contamination is
  swept 1%–10%;
* bootstrap stability — dispersion of Isolation Forest member scores across
  resamples;
* a manual-validation sample: the top ensemble anomalies with their
  data-derived reasons, for human review;
* duplicate-detection threshold curve plus known-case verification.

No accuracy/precision/recall against labels is reported, because no labels
exist. Fabricating them would violate the project's core rule.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from ml.config import MLConfig
from ml.delay_prediction.capability import assess_capability
from ml.features.engineer import MODEL_FEATURES


def method_agreement(anomaly: pd.DataFrame, methods) -> dict:
    agreement = {}
    for i, a in enumerate(methods):
        for b in methods[i + 1 :]:
            fa = anomaly[f"flag_{a}"].astype(bool)
            fb = anomaly[f"flag_{b}"].astype(bool)
            union = (fa | fb).sum()
            jaccard = float((fa & fb).sum() / union) if union else 1.0
            rho = float(stats.spearmanr(anomaly[f"score_{a}"], anomaly[f"score_{b}"]).statistic)
            agreement[f"{a}__{b}"] = {
                "flag_jaccard": round(jaccard, 3),
                "score_spearman": round(rho, 3),
                "both_flagged": int((fa & fb).sum()),
            }
    return agreement


def threshold_stability(features: pd.DataFrame, cfg: MLConfig) -> list[dict]:
    X = RobustScaler().fit_transform(features[MODEL_FEATURES].astype(float))
    rows = []
    for contamination in (0.01, 0.02, 0.05, 0.08, 0.10):
        iforest = IsolationForest(
            n_estimators=cfg.anomaly.isolation_forest_n_estimators,
            contamination=contamination,
            random_state=cfg.anomaly.isolation_forest_random_state,
            n_jobs=-1,
        ).fit(X)
        rows.append({
            "contamination": contamination,
            "flagged_count": int((iforest.predict(X) == -1).sum()),
        })
    return rows


def bootstrap_stability(features: pd.DataFrame, cfg: MLConfig, n_boot: int = 10) -> dict:
    X_full = RobustScaler().fit_transform(features[MODEL_FEATURES].astype(float))
    rng = np.random.default_rng(42)
    per_member_scores = []
    for _ in range(n_boot):
        idx = rng.choice(len(X_full), size=len(X_full), replace=True)
        iforest = IsolationForest(
            n_estimators=150,
            contamination=cfg.anomaly.contamination,
            random_state=cfg.anomaly.isolation_forest_random_state,
            n_jobs=-1,
        ).fit(X_full[idx])
        raw = -iforest.score_samples(X_full)
        lo, hi = raw.min(), raw.max()
        per_member_scores.append((raw - lo) / (hi - lo) if hi > lo else raw * 0)
    score_matrix = np.vstack(per_member_scores)
    return {
        "n_bootstrap": n_boot,
        "mean_member_score_std": round(float(score_matrix.std(axis=0).mean()), 4),
        "p95_member_score_std": round(float(np.percentile(score_matrix.std(axis=0), 95)), 4),
    }


def duplicate_threshold_curve(pairs: pd.DataFrame) -> list[dict]:
    if pairs.empty:
        return []
    curve = []
    for thr in (0.60, 0.65, 0.70, 0.72, 0.75, 0.80, 0.85):
        curve.append({
            "threshold": thr,
            "flagged_pairs": int((pairs["overall_similarity"] >= thr).sum()),
        })
    return curve


def manual_validation_sample(anomaly: pd.DataFrame, features: pd.DataFrame, k: int = 10) -> list[dict]:
    top = anomaly.sort_values("ensemble_score", ascending=False).head(k)
    feat = features.set_index("member_id")
    sample = []
    for _, row in top.iterrows():
        f = feat.loc[int(row["member_id"])]
        sample.append({
            "member_id": int(row["member_id"]),
            "mp": f["mp_name"],
            "state": f["state"],
            "constituency": f["constituency"],
            "allocation_cr": round(float(f["allocated_amount"]) / 1e7, 2) if pd.notna(f["allocated_amount"]) else None,
            "ensemble_score": float(row["ensemble_score"]),
            "votes": int(row["anomaly_votes"]),
            "reasons": list(row["anomaly_reasons"]),
        })
    return sample


def build_evaluation_report(
    features: pd.DataFrame,
    anomaly: pd.DataFrame,
    pairs: pd.DataFrame,
    risk: pd.DataFrame,
    comparison: dict,
    cfg: MLConfig,
) -> dict:
    from ml.anomaly_detection.detectors import METHODS

    level_counts = risk["risk_level"].value_counts().to_dict()
    return {
        "supervised_metrics": None,
        "supervised_metrics_note": (
            "No labelled outcomes exist in the source dataset; no supervised "
            "accuracy/precision/recall is reported (by design, not omission)."
        ),
        "delay_prediction_capability": assess_capability(),
        "anomaly_detection": {
            "method_flag_counts": comparison["methods"],
            "ensemble": comparison["ensemble"],
            "ensemble_score_distribution": {
                "mean": round(float(anomaly["ensemble_score"].mean()), 4),
                "p50": round(float(anomaly["ensemble_score"].median()), 4),
                "p90": round(float(anomaly["ensemble_score"].quantile(0.9)), 4),
                "max": round(float(anomaly["ensemble_score"].max()), 4),
            },
            "method_agreement": method_agreement(anomaly, METHODS),
            "threshold_stability": threshold_stability(features, cfg),
            "bootstrap_stability": bootstrap_stability(features, cfg),
            "manual_validation_sample": manual_validation_sample(anomaly, features),
            "false_positive_review_note": (
                "Flagged members are investigative leads. Below-benchmark allocations "
                "often reflect legitimate pro-rated terms for members elected via "
                "by-elections — reviewers must confirm membership dates before acting."
            ),
        },
        "duplicate_detection": {
            "pairs_evaluated": int(len(pairs)),
            "pairs_flagged": int(pairs["potential_duplicate"].sum()) if len(pairs) else 0,
            "threshold_curve": duplicate_threshold_curve(pairs),
            "known_case_check": _known_case_check(pairs),
            "label_policy": "POTENTIAL DUPLICATE — REQUIRES VERIFICATION",
        },
        "risk_scoring": {
            "level_counts": {k: int(v) for k, v in level_counts.items()},
            "score_distribution": {
                "mean": round(float(risk["risk_score"].mean()), 2),
                "p50": round(float(risk["risk_score"].median()), 2),
                "p90": round(float(risk["risk_score"].quantile(0.9)), 2),
                "max": round(float(risk["risk_score"].max()), 2),
            },
        },
    }


def _known_case_check(pairs: pd.DataFrame) -> dict:
    """Verify the detector surfaces the Nanded same-constituency name variant."""
    if pairs.empty:
        return {"verified": False, "note": "no pairs produced"}
    hit = pairs[
        (pairs["constituency_a"].str.lower() == "nanded")
        & (pairs["constituency_b"].str.lower() == "nanded")
    ]
    if hit.empty:
        return {"verified": False, "note": "known Nanded pair not among candidate pairs"}
    row = hit.iloc[0]
    return {
        "verified": bool(row["potential_duplicate"]),
        "pair": f"{row['mp_name_a']}  <->  {row['mp_name_b']}",
        "overall_similarity": float(row["overall_similarity"]),
        "note": "Two roster rows share the NANDED constituency and a near-identical "
                "name; one row has a blank allocation — flagged for verification.",
    }
