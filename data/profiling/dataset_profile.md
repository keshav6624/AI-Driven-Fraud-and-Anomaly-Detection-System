# MPLAD-Sentinel — Dataset Profiling Report

_Generated: 2026-08-23T09:53:52.515161+00:00_

## Allocated Limit for Honble MPs.xlsx — sheet `Sheet1`

- SHA-256: `d9367c15f624de17fdfda677af349ffe9d3bf28f3001556b81bf0db399fcba65`
- Rows (raw / excl. trailers / duplicates): 544 / 543 / 0
- Columns: 5
- Parser notes: openpyxl failed (TypeError); parsed worksheet XML directly

| Column | Role | Missing % | Unique | Mode / Top value |
|---|---|---|---|---|
| Sr. No. | numeric | 0.0% | 543 | 1 (0.18% of rows) |
| State | categorical | 0.0% | 36 | Uttar Pradesh (80) |
| Hon'ble Members of Parliaments | categorical (identifier-like) | 0.0% | 543 | AASHTIKAR PATIL NAGESH BAPURAO (1) |
| Constituency | categorical (identifier-like) | 0.0% | 542 | NANDED (2) |
| Allocated AMOUNT ( ₹ ) | numeric | 0.184% | 149 | 147,000,000 (71.77% of rows) |

**Trailer (grand-total) row detected** (excluded from analysis, retained as a checksum): [{"Sr. No.": "Grand Total", "Allocated AMOUNT ( ₹ )": "83062104294.53"}]

## Relationships / keys

- `Allocated Limit for Honble MPs.xlsx`: grain = one row per member of parliament (Sr. No. unique); candidate PK = [{'column': "Hon'ble Members of Parliaments", 'dtype': 'object', 'non_null': 543, 'missing': 0, 'missing_pct': np.float64(0.0), 'unique': 543, 'unique_pct': 100.0, 'role': 'categorical', 'top_values': {'AASHTIKAR PATIL NAGESH BAPURAO': 1, 'ABDUL RASHID SHEIKH': 1, 'ABHAY KUMAR SINHA': 1, 'ABHIJIT GANGOPADHYAY': 1, 'Abu Taher Khan': 1, 'ADHIKARI SOUMENDU': 1, 'ADITYA YADAV': 1, 'Adv Adoor Prakash': 1, 'Adv Dean Kuriakose': 1, 'ADV GOWAAL KAGADA PADAVI': 1, 'ADV K FRANCIS GEORGE': 1, 'AFZAL ANSARI': 1}, 'whitespace_issues': 1, 'likely_role': 'identifier'}, {'column': 'Constituency', 'dtype': 'object', 'non_null': 543, 'missing': 0, 'missing_pct': np.float64(0.0), 'unique': 542, 'unique_pct': 99.816, 'role': 'categorical', 'top_values': {'NANDED': 2, 'AURANGABAD_BR': 1, 'TAMLUK': 1, 'MURSHIDABAD': 1, 'KANTHI': 1, 'BADAUN': 1, 'ATTINGAL': 1, 'IDUKKI': 1, 'NANDURBAR(ST)': 1, 'KOTTAYAM': 1, 'GHAZIPUR': 1, 'SRINAGAR': 1}, 'whitespace_issues': 0, 'likely_role': 'identifier'}]

## Notes

- Single-table dataset: one row per Hon'ble MP with the MPLADS allocated amount. No project-level, transaction-level, date, expenditure or physical-progress fields exist in the provided sources.
- Post-hoc derivation policy: every derived metric used downstream must be traceable to these columns; missing information is documented, never fabricated (see docs/ml_methodology.md).