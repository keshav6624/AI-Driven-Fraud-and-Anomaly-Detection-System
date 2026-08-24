"""Central ML configuration.

Every threshold in the platform is defined here (or overridden via
environment variables prefixed with ``MPLAD_``) so that analysts can tune
sensitivity without touching code. Rationale for each default is documented
in docs/ml_methodology.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict


@dataclass(frozen=True)
class AnomalyConfig:
    # Fraction of members treated as anomalous by Isolation Forest / LOF.
    # Default 0.05 ~ top ~27 of 543 members, consistent with the heavy-tailed
    # allocation distribution observed in profiling (2.2x max / benchmark).
    contamination: float = 0.05
    isolation_forest_n_estimators: int = 300
    isolation_forest_random_state: int = 42
    lof_n_neighbors: int = 50  # large on purpose: ~72% of rows tie near the benchmark
    # Iglewicz & Hoaglin robust z-score threshold on the benchmark ratio
    robust_z_threshold: float = 3.5
    # Ensemble flags a member when at least this many methods flag it
    ensemble_vote_threshold: int = 2
    # Normalised ensemble score at/above which a member is flagged even with
    # a single voting method (guards against masked multivariate anomalies)
    ensemble_score_threshold: float = 0.80


@dataclass(frozen=True)
class DuplicateConfig:
    name_similarity_weight: float = 0.60
    constituency_similarity_weight: float = 0.25
    same_state_weight: float = 0.15
    # Pair flagged as POTENTIAL DUPLICATE at/above this overall similarity
    pair_threshold: float = 0.72
    max_pairs_per_member: int = 3
    min_name_similarity: float = 0.35


@dataclass(frozen=True)
class RiskConfig:
    """Composite risk weights. Rationale (docs/ml_methodology.md §5):

    * financial 40% — the primary mandate of the scheme is money tracking and
      the strongest signal in this dataset is allocation deviation;
    * data quality 25% — a missing/blank allocation blocks all audit trails
      and is the single most severe bookkeeping defect observable here;
    * duplicate 20% — roster duplication inflates entitlement exposure;
    * interest/rounding 15% — paise-level components indicate interest-bearing
      balances (compliance review), a weaker but real irregularity signal.
    """

    financial_weight: float = 0.40
    data_quality_weight: float = 0.25
    duplicate_weight: float = 0.20
    interest_weight: float = 0.15
    # Band ceilings calibrated on the observed composite distribution
    # (508 LOW / ~32 MEDIUM / top-3 HIGH) so that only members with severe
    # multi-signal findings reach HIGH, and the single worst bookkeeping
    # combination (duplicate roster entry + unrecorded amount) reaches
    # CRITICAL via the documented escalation rule below.
    levels: tuple = (("LOW", 25.0), ("MEDIUM", 45.0), ("HIGH", 65.0))
    # Escalate one band when a member is in a flagged potential-duplicate
    # pair AND the allocation amount is unrecorded — the strongest combined
    # bookkeeping failure observable in this dataset.
    escalate_duplicate_missing: bool = True


@dataclass(frozen=True)
class MLConfig:
    anomaly: AnomalyConfig = field(default_factory=AnomalyConfig)
    duplicate: DuplicateConfig = field(default_factory=DuplicateConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    dataset_version: str = "raw-2026-08"
    feature_version: str = "v1"
    model_version: str = "v1"

    def as_dict(self) -> dict:
        return asdict(self)


def _apply_env_overrides(cfg: MLConfig) -> MLConfig:
    """Allow MPLAD_-prefixed env vars to override numeric thresholds."""
    import dataclasses

    def parse(v: str):
        try:
            return int(v)
        except ValueError:
            return float(v)

    updates: dict[str, dict] = {}
    mapping = {
        "MPLAD_ANOMALY_CONTAMINATION": ("anomaly", "contamination"),
        "MPLAD_ROBUST_Z_THRESHOLD": ("anomaly", "robust_z_threshold"),
        "MPLAD_ENSEMBLE_VOTE_THRESHOLD": ("anomaly", "ensemble_vote_threshold"),
        "MPLAD_ENSEMBLE_SCORE_THRESHOLD": ("anomaly", "ensemble_score_threshold"),
        "MPLAD_DUPLICATE_PAIR_THRESHOLD": ("duplicate", "pair_threshold"),
    }
    for env, (section, key) in mapping.items():
        if env in os.environ:
            updates.setdefault(section, {})[key] = parse(os.environ[env])
    if not updates:
        return cfg
    sections = {}
    for name in ("anomaly", "duplicate", "risk"):
        base = getattr(cfg, name)
        if name in updates:
            base = dataclasses.replace(base, **updates[name])
        sections[name] = base
    return MLConfig(**sections)


def load_config() -> MLConfig:
    return _apply_env_overrides(MLConfig())


CONFIG = load_config()
