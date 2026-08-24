# MPLAD-Sentinel — Model Evaluation Report

_Generated: 2026-08-23T10:03:58.083191+00:00 · dataset raw-2026-08 · features v1 · model v1_

## Supervised metrics

No labelled outcomes exist in the source dataset; no supervised accuracy/precision/recall is reported (by design, not omission).

## Delay prediction capability

**NOT_BUILDABLE_WITH_CURRENT_DATASET** — Delay prediction needs project-level sanction/completion dates and a status outcome. The provided dataset is one row per Hon'ble MP with the MPLADS entitlement allocation only, so no target variable can be constructed without fabricating data — which this platform refuses to do.

## Anomaly detection (unsupervised)

- Ensemble flagged: **35 members (6.45%)** at vote≥2
- Method flag counts: robust_z=153, isolation_forest=28, lof=28
- Method agreement: robust_z__isolation_forest: J=0.183, ρ=0.78; robust_z__lof: J=0.065, ρ=0.294; isolation_forest__lof: J=0.077, ρ=0.616
- Bootstrap stability (mean member-score σ over 10 resamples): 0.019

### Manual validation sample (top-10 ensemble anomalies)

- **SK NURUL ISLAM** (West Bengal · BASIRHAT) — ₹4.9 cr, score 0.8341, 3/3 votes; Allocation is 67% below the full-entitlement benchmark (possible pro-rated term — verify membership dates); 3/3 anomaly methods agree (ensemble score 0.83)
- **EATALA RAJENDER** (Telangana · MALKAJGIRI) — ₹32.75 cr, score 0.6673, 2/3 votes; Allocation is 123% above the ₹14.7 cr full-entitlement benchmark; Non-round allocation (₹86.00 paise component) suggests interest-bearing balance accrual
- **Arvind Dharmapuri** (Telangana · NIZAMABAD) — ₹28.14 cr, score 0.5466, 2/3 votes; Allocation is 91% above the ₹14.7 cr full-entitlement benchmark; Non-round allocation (₹11.00 paise component) suggests interest-bearing balance accrual
- **Pradyut Bordoloi** (Assam · NOWGONG) — ₹9.8 cr, score 0.5462, 3/3 votes; Allocation is 33% below the full-entitlement benchmark (possible pro-rated term — verify membership dates); 3/3 anomaly methods agree (ensemble score 0.55)
- **Asit Kumar Mal** (West Bengal · BOLPUR(SC)) — ₹27.57 cr, score 0.5407, 2/3 votes; Allocation is 88% above the ₹14.7 cr full-entitlement benchmark; Non-round allocation (₹74.00 paise component) suggests interest-bearing balance accrual
- **DR. RAJESH MISHRA** (Madhya Pradesh · SIDHI) — ₹26.27 cr, score 0.5137, 2/3 votes; Allocation is 79% above the ₹14.7 cr full-entitlement benchmark; Non-round allocation (₹35.00 paise component) suggests interest-bearing balance accrual
- **Saptagiri Sankar Ulaka** (Odisha · KORAPUT(ST)) — ₹26.95 cr, score 0.5059, 2/3 votes; Allocation is 83% above the ₹14.7 cr full-entitlement benchmark; 2/3 anomaly methods agree (ensemble score 0.51)
- **Ramesh Chandappa Jigajinagi** (Karnataka · BIJAPUR(SC)) — ₹26.95 cr, score 0.5059, 2/3 votes; Allocation is 83% above the ₹14.7 cr full-entitlement benchmark; 2/3 anomaly methods agree (ensemble score 0.51)
- **ANDREW J. SYNGKON** (Meghalaya · SHILLONG) — ₹9.8 cr, score 0.4954, 3/3 votes; Allocation is 33% below the full-entitlement benchmark (possible pro-rated term — verify membership dates); 3/3 anomaly methods agree (ensemble score 0.50)
- **VARUN CHAUDHRY** (Haryana · AMBALA (SC)) — ₹25.55 cr, score 0.4714, 2/3 votes; Allocation is 74% above the ₹14.7 cr full-entitlement benchmark; 2/3 anomaly methods agree (ensemble score 0.47)

## Duplicate detection

- Pairs evaluated: 97; flagged: **1** (threshold 0.72)
- Known-case check (Nanded same-constituency variant): VERIFIED — CHAVAN VASANTRAO BALWANTRAO  <->  Ravindra Vasantrao Chavan (similarity 0.7633)

## Risk scoring

- Level counts: {'LOW': 486, 'MEDIUM': 54, 'HIGH': 2, 'CRITICAL': 1}
- Score distribution: {'mean': 8.84, 'p50': 3.4, 'p90': 27.7, 'max': 59.8}
