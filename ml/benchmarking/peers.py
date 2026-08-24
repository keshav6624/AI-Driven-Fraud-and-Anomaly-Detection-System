"""Step 6 — Peer benchmarking.

Compares each member's allocation against two peer groups that exist in the
data: (a) all members nationally and (b) members of the same state. Because
MPLADS entitlements are uniform per MP, peer groups are near-homogeneous —
which makes percentage deviations highly interpretable for auditors.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def peer_benchmark(features: pd.DataFrame) -> pd.DataFrame:
    """Attach peer comparison columns and a human-readable benchmark verdict."""
    df = features.copy()
    benchmark = float(df["benchmark_amount"].iloc[0])

    national_median = df["allocated_amount"].median()
    df["national_median_amount"] = national_median
    df["deviation_from_national_median_pct"] = (
        (df["allocated_amount"] - national_median) / national_median * 100
    )
    df["deviation_from_state_median_pct"] = df["state_deviation_pct"] * 100
    df["deviation_from_benchmark_pct"] = (df["benchmark_ratio"] - 1.0) * 100

    def verdict(row: pd.Series) -> str:
        if bool(row["amount_missing"]):
            return "ALLOCATION NOT RECORDED"
        dev = float(row["deviation_from_benchmark_pct"])
        if abs(dev) <= 0.5:
            return "AT BENCHMARK"
        if dev > 0:
            return "ABOVE BENCHMARK"
        return "BELOW BENCHMARK"

    df["benchmark_verdict"] = df.apply(verdict, axis=1)
    df["peer_state_n"] = df.groupby("state")["state"].transform("size")
    df["benchmark_amount"] = benchmark
    return df
