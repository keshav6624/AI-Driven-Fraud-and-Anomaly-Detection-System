"""Live ML inference service — runs models on-demand, not from CSVs.

This is the AI-driven core: given any MP allocation data, it runs the
full pipeline (features → anomaly detection → risk scoring → explainability)
in real-time and returns structured results.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field

from ml.config import load_config, MLConfig
from ml.features.engineer import build_features, MODEL_FEATURES
from ml.anomaly_detection.detectors import run_anomaly_detection
from ml.duplicate_detection.similarity import detect_duplicate_pairs
from ml.risk_scoring.engine import compute_risk_scores


@dataclass
class InferenceResult:
    """Full ML output for a single MP or batch."""
    member_id: int
    mp_name: str
    state: str
    constituency: str
    allocated_amount: float | None
    # Anomaly
    ensemble_score: float
    is_anomaly: bool
    anomaly_votes: int
    anomaly_reasons: list[str]
    individual_scores: dict[str, float]
    # Risk
    risk_score: float
    risk_level: str
    risk_components: dict[str, float]
    risk_escalated: bool
    # Explanation
    risk_factors: list[dict]
    recommended_actions: list[str]
    lofo_attribution: dict[str, float]
    # Duplicate
    duplicate_pairs: list[dict]


@dataclass
class BatchInferenceResult:
    results: list[InferenceResult]
    summary: dict
    model_version: str
    config_snapshot: dict


def score_single_member(
    mp_name: str,
    state: str,
    constituency: str,
    allocated_amount: float | None,
    sr_no: int = 0,
    existing_batch: pd.DataFrame | None = None,
    cfg: MLConfig | None = None,
) -> InferenceResult:
    """Score a single new MP entry against the existing dataset.

    If existing_batch is provided, the new member is scored in context
    of the existing data (for peer-relative features). Otherwise, a
    synthetic benchmark is used.
    """
    if cfg is None:
        cfg = load_config()

    new_row = pd.DataFrame([{
        "member_id": -1,
        "sr_no": sr_no,
        "state": state,
        "mp_name": mp_name,
        "mp_name_clean": mp_name.strip().title(),
        "constituency": constituency,
        "constituency_base": constituency,
        "constituency_category": "general",
        "allocated_amount": allocated_amount,
        "amount_missing": allocated_amount is None or pd.isna(allocated_amount),
        "amount_has_paise": (allocated_amount % 1 > 0) if allocated_amount and not pd.isna(allocated_amount) else False,
        "has_title_prefix": False,
        "name_case_consistent": True,
        "name_has_double_space": False,
    }])

    if existing_batch is not None and len(existing_batch) > 0:
        combined = pd.concat([existing_batch, new_row], ignore_index=True)
    else:
        combined = new_row

    features_df, _ = build_features(combined)
    # Add missing columns that the risk engine and explanations expect
    if "deviation_from_benchmark_pct" not in features_df.columns:
        bench = features_df["benchmark_amount"].iloc[0] if "benchmark_amount" in features_df.columns else 147_000_000
        features_df["deviation_from_benchmark_pct"] = (
            ((features_df["allocated_amount"] - bench) / bench * 100)
            .where(features_df["allocated_amount"].notna(), 0.0)
        )
    if "deviation_from_benchmark_pct" not in features_df.columns:
        features_df["deviation_from_benchmark_pct"] = 0.0
    new_features = features_df[features_df["member_id"] == -1].copy()
    all_features = features_df.copy()

    # Run anomaly detection on the full set to get proper peer context
    anomaly_df, anomaly_meta = run_anomaly_detection(all_features, cfg.anomaly)
    new_anomaly = anomaly_df[anomaly_df["member_id"] == -1]

    # Run duplicate detection against existing members
    dup_pairs = pd.DataFrame()
    dup_stats = {}
    if existing_batch is not None and len(existing_batch) > 0:
        existing_features = features_df[features_df["member_id"] != -1].copy()
        if len(existing_features) > 0:
            # Add the new member to the existing for pair detection
            dup_input = pd.concat([existing_features, new_features], ignore_index=True)
            dup_pairs, dup_stats = detect_duplicate_pairs(dup_input, cfg.duplicate)
            # Keep only pairs involving the new member (-1)
            dup_pairs = dup_pairs[
                (dup_pairs["member_id_a"] == -1) | (dup_pairs["member_id_b"] == -1)
            ]

    # Risk scoring
    risk_df = compute_risk_scores(all_features, anomaly_df, dup_pairs, cfg.risk)
    new_risk = risk_df[risk_df["member_id"] == -1]

    # Build explanation
    expl_merged = (
        new_risk.merge(
            new_anomaly[["member_id", "anomaly_reasons", "ensemble_score", "anomaly_votes"]],
            on="member_id", how="left"
        ).merge(
            new_features[["member_id", "state", "mp_name", "constituency",
                          "allocated_amount", "benchmark_amount",
                          "deviation_from_benchmark_pct", "paise_component",
                          "amount_missing", "name_quality_score"]],
            on="member_id", how="left"
        )
    )

    if expl_merged.empty:
        raise ValueError("Could not generate explanation for the given input")

    row = expl_merged.iloc[0]

    # Risk factors
    risk_factors = []
    weights = {
        "financial_risk": cfg.risk.financial_weight,
        "data_quality_risk": cfg.risk.data_quality_weight,
        "duplicate_risk": cfg.risk.duplicate_weight,
        "interest_risk": cfg.risk.interest_weight,
    }
    if bool(row.get("amount_missing", False)):
        risk_factors.append({
            "factor": "Allocation amount not recorded",
            "contribution_points": round(float(row.get("data_quality_risk", 0)) * weights["data_quality_risk"], 1),
            "support": "Source cell for allocated amount is blank",
        })
    dev = float(row.get("deviation_from_benchmark_pct", 0) or 0)
    if abs(dev) >= 2:
        risk_factors.append({
            "factor": f"Allocation {abs(dev):.0f}% {'above' if dev > 0 else 'below'} benchmark",
            "contribution_points": round(float(row.get("financial_risk", 0)) * weights["financial_risk"], 1),
            "support": f"₹{(allocated_amount or 0)/1e7:,.2f} cr vs benchmark ₹{float(row.get('benchmark_amount', 147000000))/1e7:.1f} cr",
        })
    if bool(row.get("flagged_duplicate_pair", False)):
        risk_factors.append({
            "factor": "Potential duplicate member record",
            "contribution_points": round(float(row.get("duplicate_risk", 0)) * weights["duplicate_risk"], 1),
            "support": f"Similarity {float(row.get('max_duplicate_similarity', 0)):.2f}",
        })
    if float(row.get("paise_component", 0) or 0) > 0:
        risk_factors.append({
            "factor": "Non-round allocation (interest component)",
            "contribution_points": round(float(row.get("interest_risk", 0)) * weights["interest_risk"], 1),
            "support": f"₹{float(row['paise_component']):.2f} paise part",
        })

    risk_factors.sort(key=lambda f: f["contribution_points"], reverse=True)

    # Recommended actions
    actions = []
    if bool(row.get("amount_missing", False)):
        actions.append("Obtain the missing allocation figure from MoSPI records")
    if dev >= 25:
        actions.append("Review sanction ledger for carry-forward/unspent balances")
    if dev <= -25:
        actions.append("Verify membership start date (pro-rated term possible)")
    if bool(row.get("flagged_duplicate_pair", False)):
        actions.append("Cross-check the matched record for duplicate entries")
    if float(row.get("paise_component", 0) or 0) > 0:
        actions.append("Reconcile interest accrual with agency bank statements")
    if not actions:
        actions.append("No immediate investigative action indicated")

    # LOFO attribution (simplified for single-member scoring)
    lofo = {}
    if not new_features.empty:
        feat_vals = new_features.iloc[0]
        for feat in MODEL_FEATURES:
            val = float(feat_vals.get(feat, 0) or 0)
            lofo[feat] = round(val, 4)

    # Duplicate pairs
    dup_list = []
    for _, dp in dup_pairs.iterrows():
        other_mid = int(dp["member_id_b"] if dp["member_id_a"] == -1 else dp["member_id_a"])
        dup_list.append({
            "member_id": other_mid,
            "mp_name": dp.get("mp_name_b" if dp["member_id_a"] == -1 else "mp_name_a", ""),
            "overall_similarity": float(dp["overall_similarity"]),
            "potential_duplicate": bool(dp["potential_duplicate"]),
            "reason": dp.get("duplicate_reason", ""),
        })

    return InferenceResult(
        member_id=-1,
        mp_name=mp_name,
        state=state,
        constituency=constituency,
        allocated_amount=allocated_amount,
        ensemble_score=float(new_anomaly.iloc[0]["ensemble_score"]) if not new_anomaly.empty else 0.0,
        is_anomaly=bool(new_anomaly.iloc[0]["is_anomaly"]) if not new_anomaly.empty else False,
        anomaly_votes=int(new_anomaly.iloc[0]["anomaly_votes"]) if not new_anomaly.empty else 0,
        anomaly_reasons=list(new_anomaly.iloc[0].get("anomaly_reasons", [])) if not new_anomaly.empty else [],
        individual_scores={
            "robust_z": float(new_anomaly.iloc[0]["score_robust_z"]) if not new_anomaly.empty else 0.0,
            "isolation_forest": float(new_anomaly.iloc[0]["score_isolation_forest"]) if not new_anomaly.empty else 0.0,
            "lof": float(new_anomaly.iloc[0]["score_lof"]) if not new_anomaly.empty else 0.0,
        },
        risk_score=float(new_risk.iloc[0]["risk_score"]) if not new_risk.empty else 0.0,
        risk_level=str(new_risk.iloc[0]["risk_level"]) if not new_risk.empty else "LOW",
        risk_components={
            "financial": float(new_risk.iloc[0]["financial_risk"]) if not new_risk.empty else 0.0,
            "data_quality": float(new_risk.iloc[0]["data_quality_risk"]) if not new_risk.empty else 0.0,
            "duplicate": float(new_risk.iloc[0]["duplicate_risk"]) if not new_risk.empty else 0.0,
            "interest": float(new_risk.iloc[0]["interest_risk"]) if not new_risk.empty else 0.0,
        },
        risk_escalated=bool(new_risk.iloc[0]["risk_escalated"]) if not new_risk.empty else False,
        risk_factors=risk_factors,
        recommended_actions=actions,
        lofo_attribution=lofo,
        duplicate_pairs=dup_list,
    )


def batch_inference(
    data: pd.DataFrame,
    cfg: MLConfig | None = None,
) -> BatchInferenceResult:
    """Run the full ML pipeline on a batch of MP data.

    Builds explanations directly from features + anomaly + risk outputs,
    avoiding the explain() module which expects non-standard column joins.
    """
    if cfg is None:
        cfg = load_config()

    features_df, meta = build_features(data)
    # Add missing columns that the risk engine and explanations expect
    if "deviation_from_benchmark_pct" not in features_df.columns:
        bench = features_df["benchmark_amount"].iloc[0] if "benchmark_amount" in features_df.columns else 147_000_000
        features_df["deviation_from_benchmark_pct"] = (
            ((features_df["allocated_amount"] - bench) / bench * 100)
            .where(features_df["allocated_amount"].notna(), 0.0)
        )
    anomaly_df, anomaly_meta = run_anomaly_detection(features_df, cfg.anomaly)
    dup_pairs, dup_stats = detect_duplicate_pairs(features_df, cfg.duplicate)
    risk_df = compute_risk_scores(features_df, anomaly_df, dup_pairs, cfg.risk)

    # Merge all results
    merged = (
        risk_df.merge(anomaly_df[["member_id", "anomaly_reasons", "ensemble_score", "anomaly_votes"]], on="member_id")
        .merge(features_df[["member_id", "state", "mp_name", "constituency",
                            "allocated_amount", "benchmark_amount",
                            "deviation_from_benchmark_pct", "paise_component",
                            "amount_missing", "name_quality_score"]], on="member_id")
    )

    weights = {
        "financial_risk": cfg.risk.financial_weight,
        "data_quality_risk": cfg.risk.data_quality_weight,
        "duplicate_risk": cfg.risk.duplicate_weight,
        "interest_risk": cfg.risk.interest_weight,
    }

    def _build_factors(row) -> list[dict]:
        factors = []
        if bool(row.get("amount_missing", False)):
            factors.append({
                "factor": "Allocation amount not recorded",
                "contribution_points": round(float(row.get("data_quality_risk", 0)) * weights["data_quality_risk"], 1),
                "support": "Source cell for allocated amount is blank",
            })
        dev = float(row.get("deviation_from_benchmark_pct", 0) or 0)
        if abs(dev) >= 2:
            factors.append({
                "factor": f"Allocation {abs(dev):.0f}% {'above' if dev > 0 else 'below'} benchmark",
                "contribution_points": round(float(row.get("financial_risk", 0)) * weights["financial_risk"], 1),
                "support": f"₹{float(row.get('allocated_amount', 0))/1e7:,.2f} cr vs benchmark ₹{float(row.get('benchmark_amount', 147000000))/1e7:.1f} cr ({int(row.get('anomaly_votes', 0))}/3 methods agree)",
            })
        if bool(row.get("flagged_duplicate_pair", False)):
            factors.append({
                "factor": "Potential duplicate member record",
                "contribution_points": round(float(row.get("duplicate_risk", 0)) * weights["duplicate_risk"], 1),
                "support": f"Similarity {float(row.get('max_duplicate_similarity', 0)):.2f}",
            })
        if float(row.get("paise_component", 0) or 0) > 0:
            factors.append({
                "factor": "Non-round allocation (interest component)",
                "contribution_points": round(float(row.get("interest_risk", 0)) * weights["interest_risk"], 1),
                "support": f"₹{float(row['paise_component']):.2f} paise part",
            })
        factors.sort(key=lambda f: f["contribution_points"], reverse=True)
        return factors

    def _build_actions(row) -> list[str]:
        actions = []
        if bool(row.get("amount_missing", False)):
            actions.append("Obtain the missing allocation figure from MoSPI records")
        dev = float(row.get("deviation_from_benchmark_pct", 0) or 0)
        if dev >= 25:
            actions.append("Review sanction ledger for carry-forward/unspent balances")
        if dev <= -25:
            actions.append("Verify membership start date (pro-rated term possible)")
        if bool(row.get("flagged_duplicate_pair", False)):
            actions.append("Cross-check the matched record for duplicate entries")
        if float(row.get("paise_component", 0) or 0) > 0:
            actions.append("Reconcile interest accrual with agency bank statements")
        if not actions:
            actions.append("No immediate investigative action indicated")
        return actions

    results = []
    for _, row in merged.iterrows():
        mid = int(row["member_id"])
        member_dups = dup_pairs[
            (dup_pairs["member_id_a"] == mid) | (dup_pairs["member_id_b"] == mid)
        ]
        dup_list = []
        for _, dp in member_dups.iterrows():
            other_mid = int(dp["member_id_b"] if dp["member_id_a"] == mid else dp["member_id_a"])
            dup_list.append({
                "member_id": other_mid,
                "overall_similarity": float(dp["overall_similarity"]),
                "potential_duplicate": bool(dp["potential_duplicate"]),
            })

        lofo = {}
        feat_row = features_df[features_df["member_id"] == mid]
        if not feat_row.empty:
            for feat in MODEL_FEATURES:
                val = float(feat_row.iloc[0].get(feat, 0) or 0)
                lofo[feat] = round(val, 4)

        reasons_raw = row.get("anomaly_reasons", [])
        reasons = reasons_raw if isinstance(reasons_raw, list) else []

        results.append(InferenceResult(
            member_id=mid,
            mp_name=str(row.get("mp_name", "")),
            state=str(row.get("state", "")),
            constituency=str(row.get("constituency", "")),
            allocated_amount=float(row.get("allocated_amount", 0)),
            ensemble_score=float(row.get("ensemble_score", 0)),
            is_anomaly=bool(row.get("is_anomaly", False)),
            anomaly_votes=int(row.get("anomaly_votes", 0)),
            anomaly_reasons=reasons,
            individual_scores={},
            risk_score=float(row.get("risk_score", 0)),
            risk_level=str(row.get("risk_level", "LOW")),
            risk_components={
                "financial": float(row.get("financial_risk", 0)),
                "data_quality": float(row.get("data_quality_risk", 0)),
                "duplicate": float(row.get("duplicate_risk", 0)),
                "interest": float(row.get("interest_risk", 0)),
            },
            risk_escalated=bool(row.get("risk_escalated", False)),
            risk_factors=_build_factors(row),
            recommended_actions=_build_actions(row),
            lofo_attribution=lofo,
            duplicate_pairs=dup_list,
        ))

    summary = {
        "total_members": len(results),
        "anomalies_detected": sum(1 for r in results if r.is_anomaly),
        "anomaly_rate": round(sum(1 for r in results if r.is_anomaly) / len(results) * 100, 2) if results else 0,
        "risk_distribution": {
            level: sum(1 for r in results if r.risk_level == level)
            for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        },
        "duplicate_pairs_flagged": dup_stats.get("pairs_above_threshold", 0),
        "model_version": cfg.model_version,
    }

    return BatchInferenceResult(
        results=results,
        summary=summary,
        model_version=cfg.model_version,
        config_snapshot=cfg.as_dict(),
    )
