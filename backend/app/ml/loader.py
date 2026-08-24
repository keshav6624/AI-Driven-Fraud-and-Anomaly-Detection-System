"""ML integration service — live scoring and explanations from processed data."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"


def _load(name: str) -> pd.DataFrame:
    p = DATA_DIR / name
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()


class MLLoader:
    """Lazy-loading cache for processed ML dataframes."""

    def __init__(self):
        self._features: pd.DataFrame | None = None
        self._anomalies: pd.DataFrame | None = None
        self._risk: pd.DataFrame | None = None
        self._explanations: pd.DataFrame | None = None
        self._duplicates: pd.DataFrame | None = None

    @property
    def features(self) -> pd.DataFrame:
        if self._features is None:
            self._features = _load("mp_features.csv")
        return self._features

    @property
    def anomalies(self) -> pd.DataFrame:
        if self._anomalies is None:
            self._anomalies = _load("mp_anomalies.csv")
        return self._anomalies

    @property
    def risk(self) -> pd.DataFrame:
        if self._risk is None:
            self._risk = _load("mp_risk_scores.csv")
        return self._risk

    @property
    def explanations(self) -> pd.DataFrame:
        if self._explanations is None:
            self._explanations = _load("mp_explanations.csv")
        return self._explanations

    @property
    def duplicates(self) -> pd.DataFrame:
        if self._duplicates is None:
            self._duplicates = _load("duplicate_pairs.csv")
        return self._duplicates

    def reload(self):
        self._features = None
        self._anomalies = None
        self._risk = None
        self._explanations = None
        self._duplicates = None


ml_loader = MLLoader()
