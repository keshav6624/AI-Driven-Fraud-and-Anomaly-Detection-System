"""Steps 4–10 — Analytical transform.

Runs the full ML chain over the cleaned allocation table and writes the
processed analytical tables consumed by the loader and evaluation:

  mp_features.csv       engineered features + peer benchmarks
  mp_anomalies.csv      per-method scores, ensemble flags, reasons
  duplicate_pairs.csv   candidate similar-record pairs
  mp_risk_scores.csv    composite risk scores + components
  mp_explanations.csv   factors, supporting metrics, LOFO attribution,
                        recommended actions
  evaluation_report.json / .md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml.anomaly_detection import run_anomaly_detection
from ml.benchmarking import peer_benchmark
from ml.config import load_config
from ml.duplicate_detection import detect_duplicate_pairs
from ml.evaluation import build_evaluation_report
from ml.explainability import explain
from ml.features import build_features
from ml.risk_scoring import compute_risk_scores
from pipelines.clean import clean_allocations

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
PROFILING_DIR = ROOT / "data" / "profiling"


def run_transform() -> dict:
    cfg = load_config()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    clean_df, _ = clean_allocations()
    features, feature_meta = build_features(clean_df)
    features = peer_benchmark(features)

    anomaly, comparison = run_anomaly_detection(features, cfg.anomaly)
    pairs, dup_stats = detect_duplicate_pairs(features, cfg.duplicate)
    risk = compute_risk_scores(features, anomaly, pairs, cfg.risk)
    explanations = explain(features, anomaly, risk, cfg)

    evaluation = build_evaluation_report(features, anomaly, pairs, risk, comparison, cfg)
    evaluation["run_metadata"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": cfg.dataset_version,
        "feature_version": cfg.feature_version,
        "model_version": cfg.model_version,
        "config": cfg.as_dict(),
        "feature_metadata": feature_meta,
    }

    features.to_csv(PROCESSED_DIR / "mp_features.csv", index=False)
    anomaly.to_csv(PROCESSED_DIR / "mp_anomalies.csv", index=False)
    pairs.to_csv(PROCESSED_DIR / "duplicate_pairs.csv", index=False)
    risk.to_csv(PROCESSED_DIR / "mp_risk_scores.csv", index=False)
    explanations.to_csv(PROCESSED_DIR / "mp_explanations.csv", index=False)
    (PROFILING_DIR / "evaluation_report.json").write_text(
        json.dumps(evaluation, indent=2, default=str), encoding="utf-8"
    )
    (PROFILING_DIR / "evaluation_report.md").write_text(_markdown(evaluation), encoding="utf-8")

    summary = {
        "members": len(features),
        "anomalies_flagged": int(anomaly["is_anomaly"].sum()),
        "duplicate_pairs_flagged": int(pairs["potential_duplicate"].sum()) if len(pairs) else 0,
        "risk_levels": risk["risk_level"].value_counts().to_dict(),
        "high_or_critical": int(risk["risk_level"].isin(["HIGH", "CRITICAL"]).sum()),
    }
    print(f"[transform] {json.dumps(summary, default=str)}")
    return summary


def _markdown(ev: dict) -> str:
    a = ev["anomaly_detection"]
    d = ev["duplicate_detection"]
    r = ev["risk_scoring"]
    lines = [
        "# MPLAD-Sentinel — Model Evaluation Report", "",
        f"_Generated: {ev['run_metadata']['generated_at']} · "
        f"dataset {ev['run_metadata']['dataset_version']} · "
        f"features {ev['run_metadata']['feature_version']} · "
        f"model {ev['run_metadata']['model_version']}_", "",
        "## Supervised metrics", "",
        ev["supervised_metrics_note"], "",
        "## Delay prediction capability", "",
        f"**{ev['delay_prediction_capability']['verdict']}** — "
        + ev["delay_prediction_capability"]["reason"], "",
        "## Anomaly detection (unsupervised)", "",
        f"- Ensemble flagged: **{a['ensemble']['flagged_count']} members "
        f"({a['ensemble']['flagged_pct']}%)** at vote≥{a['ensemble']['vote_threshold']}",
        f"- Method flag counts: "
        + ", ".join(f"{m}={v['flagged_count']}" for m, v in a["method_flag_counts"].items()),
        f"- Method agreement: "
        + "; ".join(f"{k}: J={v['flag_jaccard']}, ρ={v['score_spearman']}"
                    for k, v in a["method_agreement"].items()),
        f"- Bootstrap stability (mean member-score σ over {a['bootstrap_stability']['n_bootstrap']} "
        f"resamples): {a['bootstrap_stability']['mean_member_score_std']}", "",
        "### Manual validation sample (top-10 ensemble anomalies)", "",
    ]
    for s in a["manual_validation_sample"]:
        lines.append(f"- **{s['mp']}** ({s['state']} · {s['constituency']}) — "
                     f"₹{s['allocation_cr']} cr, score {s['ensemble_score']}, "
                     f"{s['votes']}/3 votes; {'; '.join(s['reasons'][:2])}")
    lines += [
        "", "## Duplicate detection", "",
        f"- Pairs evaluated: {d['pairs_evaluated']}; flagged: **{d['pairs_flagged']}** "
        f"(threshold {d.get('threshold_curve') and 0.72})",
        f"- Known-case check (Nanded same-constituency variant): "
        f"{'VERIFIED' if d['known_case_check']['verified'] else 'NOT VERIFIED'}"
        + (f" — {d['known_case_check']['pair']} "
           f"(similarity {d['known_case_check']['overall_similarity']})"
           if d["known_case_check"].get("pair") else ""),
        "", "## Risk scoring", "",
        f"- Level counts: {r['level_counts']}",
        f"- Score distribution: {r['score_distribution']}", "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    run_transform()
