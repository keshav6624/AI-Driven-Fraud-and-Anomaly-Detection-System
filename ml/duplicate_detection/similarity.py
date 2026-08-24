"""Step 7 — Duplicate / similar record detection.

The dataset has no free-text project descriptions; the textual surface
available for semantic matching is the member name, reinforced by
structured signals (constituency, state). Pipeline:

1. TF-IDF over character 3–5 grams of the cleaned name (robust to
   'CHAVAN VASANTRAO' vs 'Ravindra Vasantrao Chavan' style variants)
   blended with token-set overlap;
2. constituency similarity via token Jaccard on the base constituency name;
3. a same-state signal (duplicates inside one state are far more damaging).

Every flagged pair is labelled POTENTIAL DUPLICATE — REQUIRES VERIFICATION.
No pair is ever labelled fraudulent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from ml.config import DuplicateConfig


def _token_set(s: str) -> set[str]:
    return set(s.lower().split())


def _token_jaccard(a: str, b: str) -> float:
    ta, tb = _token_set(a), _token_set(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def name_similarity_matrix(names: pd.Series) -> np.ndarray:
    """Blend char-TFIDF cosine with token-Jaccard on the raw name tokens."""
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True)
    m = char_vec.fit_transform(names.astype(str))
    cosine = (m @ m.T).toarray()

    jac = np.zeros_like(cosine)
    token_sets = [_token_set(n) for n in names.astype(str)]
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            ta, tb = token_sets[i], token_sets[j]
            sim = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
            jac[i, j] = jac[j, i] = sim
    return 0.5 * cosine + 0.5 * jac


def detect_duplicate_pairs(
    features: pd.DataFrame, cfg: DuplicateConfig
) -> tuple[pd.DataFrame, dict]:
    names = features["mp_name_clean"].reset_index(drop=True)
    cons = features["constituency_base"].reset_index(drop=True)
    states = features["state"].reset_index(drop=True)
    ids = features["member_id"].reset_index(drop=True)

    name_sim = name_similarity_matrix(names)
    n = len(names)

    records: list[dict] = []
    for i in range(n):
        for j in range(i + 1, n):
            cons_sim = _token_jaccard(cons[i], cons[j])
            same_state = float(states[i] == states[j])
            overall = (
                cfg.name_similarity_weight * name_sim[i, j]
                + cfg.constituency_similarity_weight * cons_sim
                + cfg.same_state_weight * same_state
            )
            if name_sim[i, j] < cfg.min_name_similarity and cons_sim < 0.99:
                continue
            records.append(
                {
                    "member_id_a": int(ids[i]),
                    "member_id_b": int(ids[j]),
                    "mp_name_a": names[i],
                    "mp_name_b": names[j],
                    "state_a": states[i],
                    "state_b": states[j],
                    "constituency_a": cons[i],
                    "constituency_b": cons[j],
                    "name_similarity": round(float(name_sim[i, j]), 4),
                    "constituency_similarity": round(float(cons_sim), 4),
                    "same_state": bool(same_state),
                    "overall_similarity": round(float(overall), 4),
                }
            )

    pairs = pd.DataFrame(records)
    if pairs.empty:
        return pairs, {"pairs_above_threshold": 0}

    pairs = pairs.sort_values("overall_similarity", ascending=False).reset_index(drop=True)
    pairs["potential_duplicate"] = pairs["overall_similarity"] >= cfg.pair_threshold

    def reason(row: pd.Series) -> str:
        bits = []
        if row["same_state"]:
            bits.append("same state")
        if row["constituency_similarity"] > 0.6:
            bits.append("similar constituency name")
        elif row["constituency_similarity"] > 0.99:
            bits.append("IDENTICAL constituency name")
        bits.append(f"name similarity {row['name_similarity']:.2f}")
        return "POTENTIAL DUPLICATE — REQUIRES VERIFICATION (" + "; ".join(bits) + ")"

    pairs["duplicate_reason"] = pairs.apply(reason, axis=1)

    # keep the strongest pairs per member to avoid explosion of near-noise pairs
    keep_idx: list[int] = []
    counts: dict[int, int] = {}
    for idx, row in pairs.iterrows():
        a, b = int(row["member_id_a"]), int(row["member_id_b"])
        if counts.get(a, 0) >= cfg.max_pairs_per_member:
            continue
        if counts.get(b, 0) >= cfg.max_pairs_per_member:
            continue
        keep_idx.append(idx)
        counts[a] = counts.get(a, 0) + 1
        counts[b] = counts.get(b, 0) + 1
    pairs = pairs.loc[keep_idx].reset_index(drop=True)

    flagged = pairs[pairs["potential_duplicate"]]
    stats = {
        "pairs_evaluated": int(len(pairs)),
        "pairs_above_threshold": int(len(flagged)),
        "threshold": cfg.pair_threshold,
        "weights": {
            "name": cfg.name_similarity_weight,
            "constituency": cfg.constituency_similarity_weight,
            "same_state": cfg.same_state_weight,
        },
        "top_pair": (
            flagged.iloc[0][["mp_name_a", "mp_name_b", "overall_similarity"]].to_dict()
            if len(flagged)
            else None
        ),
    }
    return pairs, stats
