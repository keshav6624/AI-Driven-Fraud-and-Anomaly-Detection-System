# MPLAD-Sentinel — AI-Driven Anomaly Detection for MPLADS

**An AI/ML-powered platform for detecting anomalies, fraud indicators, and inefficiencies in Member of Parliament Local Area Development Scheme (MPLADS) data.**

Built for **Smart India Hackathon 2026** — Problem Statement **SIH26102**: *AI-Driven Fraud and Anomaly Detection System for MPLADS Data Analytics Portal*.

This is a full-stack platform with a **FastAPI** backend serving live ML inference, a **React + TypeScript** frontend with ECharts/MapLibre visualizations, and an end-to-end ML pipeline (unsupervised anomaly detection, risk scoring, duplicate detection, NL2SQL assistant, explainability).

---

## Architecture

```
mpclad/
│
├── backend/                          # FastAPI REST API
│   ├── app/
│   │   ├── main.py                   # App entry, CORS, lifespan DB init
│   │   ├── config.py                 # Pydantic-settings (env-driven)
│   │   ├── api/
│   │   │   ├── deps.py               # JWT auth + RBAC dependencies
│   │   │   ├── auth.py               # Login, user management
│   │   │   ├── projects.py           # Project (MP allocation) CRUD
│   │   │   ├── analytics.py          # Dashboard aggregations
│   │   │   ├── map_routes.py         # GeoJSON map data
│   │   │   ├── investigation.py      # Investigation case management
│   │   │   └── ml_routes.py          # AI endpoints (scoring, NL2SQL, batch)
│   │   ├── schemas/                  # Pydantic v2 request/response models
│   │   ├── services/                 # Business logic layer
│   │   ├── models/orm.py             # SQLAlchemy ORM (14 tables)
│   │   ├── ml/
│   │   │   ├── inference.py          # Live ML scoring engine
│   │   │   ├── assistant.py          # NL2SQL natural language queries
│   │   │   └── loader.py             # Processed data loader
│   │   ├── analytics/                # Dashboard aggregation helpers
│   │   ├── database/session.py       # Engine + session management
│   │   └── utils/security.py         # PBKDF2 + JWT utilities
│   ├── scripts/seed_data.py          # DB seeder (CSV → SQLite/PostgreSQL)
│   ├── tests/                        # 26 pytest tests
│   └── requirements.txt
│
├── ml/                               # ML Pipeline Modules
│   ├── config.py                     # Thresholds (AnomalyConfig, RiskConfig, ...)
│   ├── features/engineer.py          # 9-feature analytical matrix
│   ├── anomaly_detection/detectors.py # Robust Z + Isolation Forest + LOF
│   ├── benchmarking/peers.py         # National/state median comparison
│   ├── duplicate_detection/similarity.py # TF-IDF + Jaccard similarity
│   ├── risk_scoring/engine.py        # Composite 0–100 risk score
│   └── explainability/explainer.py   # LOFO attribution + component decomposition
│
├── pipelines/                        # ETL + ML Orchestration
│   ├── clean.py                      # Raw CSV → cleaned DataFrame
│   └── transform.py                  # Full ML chain runner
│
├── data/
│   ├── raw/                          # Source dataset (543 MP allocations)
│   └── processed/                    # Feature-engineered CSVs
│
├── frontend/                         # React + TypeScript SPA (Vite)
│   ├── src/
│   │   ├── main.tsx / App.tsx        # Entry + 13 routes
│   │   ├── api/client.ts             # Typed API client
│   │   ├── contexts/AuthContext.tsx   # JWT auth state
│   │   ├── components/Layout.tsx     # Sidebar + outlet
│   │   └── pages/
│   │       ├── Login.tsx             # JWT login
│   │       ├── Dashboard.tsx         # ECharts overview (pie, bar)
│   │       ├── Projects.tsx          # Filterable project table
│   │       ├── ProjectDetail.tsx     # Full member detail (gauge, radar)
│   │       ├── RiskDashboard.tsx     # Risk scatter, stacked bar
│   │       ├── Anomalies.tsx         # Anomaly scatter + histogram
│   │       ├── Duplicates.tsx        # Similarity pairs table
│   │       ├── MapView.tsx           # MapLibre GL choropleth
│   │       ├── Investigations.tsx    # Case CRUD + notes
│   │       ├── Assistant.tsx         # AI chat interface (NL2SQL)
│   │       ├── Scoring.tsx           # Real-time ML scoring form
│   │       ├── Admin.tsx             # User management
│   │       └── About.tsx             # Project info
│   ├── package.json
│   ├── vite.config.ts                # Dev proxy: /api → :8000
│   └── tailwind.config.js
│
├── docker-compose.yml                # PostgreSQL + backend + frontend
├── Dockerfile                        # Backend container
└── README.md
```

---
SCREENSHOT



## Quick Start (Development)

### 1. Backend (port 8000)

```bash
cd mpclad
pip install -r backend/requirements.txt
python -m backend.scripts.seed_data    # Seed DB from processed CSVs
uvicorn backend.app.main:app --reload  # http://localhost:8000/docs
```

**Login:** `admin` / `admin-changeMe`

### 2. Frontend (port 5173)

```bash
cd mpclad/frontend
npm install
npm run dev                            # http://localhost:5173
```

Vite proxies `/auth`, `/projects`, `/analytics`, `/map`, `/investigations`, `/ml` to `http://localhost:8000`.

### 3. Tests

```bash
python -m pytest backend/tests/ -v
```

---

## AI/ML Pipeline

| Stage | Module | Description |
|-------|--------|-------------|
| 1. Feature Engineering | `ml/features/engineer.py` | 9 analytical features (benchmark ratio, log amount, percentiles, paise component, name quality) |
| 2. Anomaly Detection | `ml/anomaly_detection/detectors.py` | Ensemble of Robust Z-Score, Isolation Forest, LOF — 2/3 vote threshold |
| 3. Peer Benchmarking | `ml/benchmarking/peers.py` | National + state-level median comparisons |
| 4. Duplicate Detection | `ml/duplicate_detection/similarity.py` | TF-IDF char 3–5 grams + token Jaccard + constituency similarity |
| 5. Risk Scoring | `ml/risk_scoring/engine.py` | Composite 0–100 (financial 40%, data quality 25%, duplicate 20%, interest 15%) |
| 6. Explainability | `ml/explainability/explainer.py` | Leave-one-feature-out (LOFO) attribution + component decomposition |

```
Final risk score (0–100) = 0.40 × financial_risk
                         + 0.25 × data_quality_risk
                         + 0.20 × duplicate_risk
                         + 0.15 × interest_risk

Bands: LOW < 25 | MEDIUM < 45 | HIGH < 65 | CRITICAL ≥ 65
Escalation: +1 band when duplicate flag AND missing amount
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | JWT login → token |
| POST | `/auth/users` | Create user (ADMIN) |
| GET | `/projects` | List projects (paginated, filterable) |
| GET | `/projects/{id}` | Full project detail with ML scores |
| GET | `/projects/meta/states` | List all states |
| GET | `/analytics/overview` | Dashboard overview |
| GET | `/analytics/risk-distribution` | Risk level counts |
| GET | `/analytics/anomaly/scatter` | Anomaly scatter data |
| GET | `/analytics/anomaly/distribution` | Score histogram |
| GET | `/analytics/duplicates` | Duplicate pair list |
| GET | `/analytics/duplicates/summary` | Duplicate summary stats |
| GET | `/map/projects` | GeoJSON map points |
| POST | `/investigations` | Create investigation case |
| GET | `/investigations` | List cases (paginated) |
| GET | `/investigations/{id}` | Case detail + notes |
| PATCH | `/investigations/{id}` | Update case status |
| POST | `/investigations/{id}/notes` | Add case note |
| **POST** | **`/ml/score`** | **AI: Real-time scoring for any MP** |
| **POST** | **`/ml/batch`** | **AI: Re-run full ML pipeline on all data** |
| **POST** | **`/ml/ask`** | **AI: Natural language → SQL → answer** |
| **POST** | **`/ml/retrain`** | **AI: Retrain all models** |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Docker

```bash
docker compose up --build
# Frontend:  http://localhost:5173
# Backend:   http://localhost:8000
# API docs:  http://localhost:8000/docs
# PostgreSQL: localhost:5432
```

---

## Key Dependencies

**Backend:** FastAPI, SQLAlchemy 2.x, pandas, scikit-learn, PyJWT, Pydantic v2

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, ECharts, MapLibre GL

**ML:** scikit-learn (Isolation Forest, LOF, TF-IDF, RobustScaler), numpy, scipy

**Auth:** PBKDF2-HMAC-SHA256 (240k iterations), JWT (HS256)

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./data/mplad_dev.db` | PostgreSQL or SQLite connection |
| `JWT_SECRET` | `change-me-in-env` | HS256 signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Token TTL |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | Allowed origins |
| `SEED_ADMIN_PASSWORD` | `admin-changeMe` | Default admin password |
| `ENV` | `development` | Runtime environment |
| `MPLAD_ANOMALY_CONTAMINATION` | `0.05` | IF/LOF contamination rate |
| `MPLAD_ROBUST_Z_THRESHOLD` | `3.5` | Robust z-score threshold |
| `MPLAD_ENSEMBLE_VOTE_THRESHOLD` | `2` | Methods required to flag |
| `MPLAD_DUPLICATE_PAIR_THRESHOLD` | `0.72` | Duplicate pair threshold |

---

## Data Disclaimer

This platform monitors anomalies and irregularities for investigation purposes. Terms like "anomaly", "risk", and "potential duplication" do **not** imply fraud. All findings require human verification before any action is taken.

---

## License

MIT
