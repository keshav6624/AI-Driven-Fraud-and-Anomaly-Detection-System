"""Step 8 — Delay prediction: capability assessment.

The spec requires delay prediction to be built ONLY when the dataset
supports a leakage-free target. The provided dataset contains a single
financial column per MP (allocated entitlement) — no sanction dates, no
completion dates, no project status, no expenditure and no physical
progress. There is therefore no definable 'delay' outcome.

This module makes that determination programmatically (so the platform UI
and evaluation report state it from an auditable check, not an assertion),
and refuses to train if invoked. When richer MPLADS work-report data is
added to data/raw/, extend REQUIRED_FIELDS and implement the trainer —
the surrounding pipeline slots are already in place.
"""
from __future__ import annotations

REQUIRED_FIELDS: dict[str, list[str]] = {
    "temporal": ["sanction_date", "completion_date_or_due_date"],
    "status": ["project_status"],
    "financial_context": ["sanctioned_amount_or_expenditure"],
}

AVAILABLE_FIELDS = [
    "sr_no", "state", "mp_name", "constituency", "allocated_amount",
]


class DelayPredictionNotSupported(RuntimeError):
    """Raised if a training attempt is made without the required fields."""


def assess_capability(source_columns: list[str] | None = None) -> dict:
    columns = {c.lower() for c in (source_columns or AVAILABLE_FIELDS)}
    missing: dict[str, list[str]] = {}
    for group, fields in REQUIRED_FIELDS.items():
        gaps = [f for f in fields if not any(f.split("_")[0] in c for c in columns)]
        missing[group] = gaps
    buildable = all(not gaps for gaps in missing.values())
    return {
        "capability": "project_delay_prediction",
        "verdict": "BUILDABLE" if buildable else "NOT_BUILDABLE_WITH_CURRENT_DATASET",
        "required_field_groups": REQUIRED_FIELDS,
        "missing_by_group": missing,
        "reason": (
            "Delay prediction needs project-level sanction/completion dates and a status "
            "outcome. The provided dataset is one row per Hon'ble MP with the MPLADS "
            "entitlement allocation only, so no target variable can be constructed "
            "without fabricating data — which this platform refuses to do."
        ) if not buildable else "All required field groups present.",
        "recovery_path": (
            "Add MoSPI MPLADS work-report extracts (sanctions with dates, completion "
            "status, expenditure) to data/raw/ and re-run pipelines.profile — the "
            "profiler will surface the new schema and this assessment flips to BUILDABLE."
        ),
    }


def train(*args, **kwargs):  # pragma: no cover - guard rail
    raise DelayPredictionNotSupported(
        "Delay prediction cannot be trained on the current dataset (no temporal/status "
        "fields). See ml/delay_prediction/capability.py."
    )
