-- MPLAD-Sentinel schema (PostgreSQL)
-- Grain note: the source dataset is one row per Hon'ble MP (entitlement
-- allocation). The schema is normalised around that grain; project/works
-- tables are deliberately absent because no such data exists in the
-- provided sources (see docs/data_dictionary.md).

BEGIN;

CREATE TYPE user_role      AS ENUM ('ADMIN','ANALYST','INVESTIGATOR','VIEWER');
CREATE TYPE risk_level_t   AS ENUM ('LOW','MEDIUM','HIGH','CRITICAL');
CREATE TYPE case_status_t  AS ENUM ('OPEN','UNDER_REVIEW','VERIFIED','DISMISSED','RESOLVED');
CREATE TYPE case_priority_t AS ENUM ('LOW','MEDIUM','HIGH','URGENT');

CREATE TABLE states (
    state_id  SERIAL PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE
);

CREATE TABLE constituencies (
    constituency_id SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    base_name       TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'general',  -- general | sc | st
    state_id        INTEGER NOT NULL REFERENCES states(state_id),
    UNIQUE (name, state_id)
);

CREATE TABLE members (
    member_id         INTEGER PRIMARY KEY,          -- stable surrogate from ETL
    sr_no             INTEGER UNIQUE,               -- source serial number
    state_id          INTEGER NOT NULL REFERENCES states(state_id),
    constituency_id   INTEGER NOT NULL REFERENCES constituencies(constituency_id),
    mp_name_raw       TEXT NOT NULL,                -- original values preserved
    mp_name           TEXT NOT NULL,
    mp_name_clean     TEXT NOT NULL,
    member_key        TEXT NOT NULL UNIQUE,
    name_quality_score NUMERIC(4,3) NOT NULL,
    has_title_prefix  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE entitlements (
    entitlement_id      SERIAL PRIMARY KEY,
    member_id           INTEGER NOT NULL UNIQUE REFERENCES members(member_id) ON DELETE CASCADE,
    allocated_amount    NUMERIC(16,2),              -- NULL = blank in source
    amount_missing      BOOLEAN NOT NULL,
    amount_has_paise    BOOLEAN NOT NULL,
    allocated_amount_raw TEXT,
    source_file         TEXT NOT NULL,
    dataset_version     TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE mp_features (
    member_id        INTEGER PRIMARY KEY REFERENCES members(member_id) ON DELETE CASCADE,
    benchmark_amount NUMERIC(16,2) NOT NULL,
    benchmark_ratio  NUMERIC(10,6),
    deviation_from_benchmark_pct NUMERIC(10,4),
    state_deviation_pct NUMERIC(10,4),
    state_percentile NUMERIC(6,4),
    national_percentile NUMERIC(6,4),
    paise_component  NUMERIC(12,2),
    excess_over_benchmark_cr NUMERIC(12,4),
    shortfall_ratio  NUMERIC(10,6),
    benchmark_verdict TEXT NOT NULL,
    peer_state_n     INTEGER NOT NULL,
    feature_version  TEXT NOT NULL
);

CREATE TABLE member_anomalies (
    member_id  INTEGER PRIMARY KEY REFERENCES members(member_id) ON DELETE CASCADE,
    score_robust_z          NUMERIC(8,4) NOT NULL,
    flag_robust_z           BOOLEAN NOT NULL,
    score_isolation_forest  NUMERIC(8,4) NOT NULL,
    flag_isolation_forest   BOOLEAN NOT NULL,
    score_lof               NUMERIC(8,4) NOT NULL,
    flag_lof                BOOLEAN NOT NULL,
    anomaly_votes           INTEGER NOT NULL,
    ensemble_score          NUMERIC(8,4) NOT NULL,
    is_anomaly              BOOLEAN NOT NULL,
    reasons                 JSONB NOT NULL DEFAULT '[]',
    model_version           TEXT NOT NULL,
    detected_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE risk_scores (
    member_id   INTEGER PRIMARY KEY REFERENCES members(member_id) ON DELETE CASCADE,
    risk_score  NUMERIC(6,2) NOT NULL,
    risk_level  risk_level_t NOT NULL,
    financial_risk    NUMERIC(6,2) NOT NULL,
    data_quality_risk NUMERIC(6,2) NOT NULL,
    duplicate_risk    NUMERIC(6,2) NOT NULL,
    interest_risk     NUMERIC(6,2) NOT NULL,
    max_duplicate_similarity NUMERIC(6,4),
    flagged_duplicate_pair   BOOLEAN NOT NULL DEFAULT FALSE,
    risk_escalated           BOOLEAN NOT NULL DEFAULT FALSE,
    model_version   TEXT NOT NULL,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE member_explanations (
    member_id  INTEGER PRIMARY KEY REFERENCES members(member_id) ON DELETE CASCADE,
    risk_factors       JSONB NOT NULL DEFAULT '[]',
    recommended_actions JSONB NOT NULL DEFAULT '[]',
    lofo_attribution   JSONB NOT NULL DEFAULT '{}',
    model_version      TEXT NOT NULL
);

CREATE TABLE duplicate_pairs (
    pair_id     SERIAL PRIMARY KEY,
    member_id_a INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    member_id_b INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    name_similarity         NUMERIC(6,4) NOT NULL,
    constituency_similarity NUMERIC(6,4) NOT NULL,
    same_state              BOOLEAN NOT NULL,
    overall_similarity      NUMERIC(6,4) NOT NULL,
    potential_duplicate     BOOLEAN NOT NULL,
    reason                  TEXT NOT NULL,
    model_version           TEXT NOT NULL,
    CHECK (member_id_a < member_id_b)
);

CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          user_role NOT NULL DEFAULT 'VIEWER',
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE investigation_cases (
    case_id       SERIAL PRIMARY KEY,
    member_id     INTEGER NOT NULL REFERENCES members(member_id),
    title         TEXT NOT NULL,
    description   TEXT,
    status        case_status_t NOT NULL DEFAULT 'OPEN',
    priority      case_priority_t NOT NULL DEFAULT 'MEDIUM',
    created_by    INTEGER NOT NULL REFERENCES users(user_id),
    assigned_to   INTEGER REFERENCES users(user_id),
    resolution_notes TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE case_notes (
    note_id   SERIAL PRIMARY KEY,
    case_id   INTEGER NOT NULL REFERENCES investigation_cases(case_id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(user_id),
    body      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE model_runs (
    run_id         SERIAL PRIMARY KEY,
    run_type       TEXT NOT NULL,          -- etl | anomaly | duplicate | risk | evaluation
    model_version  TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    metrics        JSONB NOT NULL DEFAULT '{}',
    notes          TEXT,
    executed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE assistant_query_log (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(user_id),
    question    TEXT NOT NULL,
    intent      TEXT NOT NULL,
    sql_text    TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    answered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Operational indexes (spec: identifiers, state, constituency, dates, risk, anomaly status)
CREATE INDEX idx_members_state        ON members(state_id);
CREATE INDEX idx_members_constituency  ON members(constituency_id);
CREATE INDEX idx_members_name_clean    ON members(mp_name_clean);
CREATE INDEX idx_risk_level_score      ON risk_scores(risk_level, risk_score DESC);
CREATE INDEX idx_anomalies_is_anomaly  ON member_anomalies(is_anomaly) WHERE is_anomaly;
CREATE INDEX idx_anomalies_ensemble    ON member_anomalies(ensemble_score DESC);
CREATE INDEX idx_dup_pairs_flagged     ON duplicate_pairs(potential_duplicate) WHERE potential_duplicate;
CREATE INDEX idx_cases_status          ON investigation_cases(status);
CREATE INDEX idx_cases_member          ON investigation_cases(member_id);
CREATE INDEX idx_entitlements_amount   ON entitlements(allocated_amount);
CREATE INDEX idx_notes_case            ON case_notes(case_id);

COMMIT;
