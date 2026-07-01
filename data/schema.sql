-- data/schema.sql
-- Production PostgreSQL schema for Supabase.
-- Run this once on your Supabase project: Settings → SQL Editor → Run.
-- The SQLite dev.db schema (in generate_data.py) is a subset of this.

-- ── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- fuzzy text search on names

-- ── Applicants ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applicants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name           TEXT NOT NULL,
    email               TEXT UNIQUE NOT NULL,
    phone               TEXT,
    date_of_birth       DATE,
    pan_number          TEXT UNIQUE,
    aadhaar_last4       CHAR(4),
    employer_name       TEXT,
    employment_type     TEXT CHECK (employment_type IN ('salaried','self_employed_professional','business')),
    designation         TEXT,
    monthly_income      NUMERIC(14, 2) NOT NULL DEFAULT 0,
    years_employed      NUMERIC(5, 1),
    residential_status  TEXT CHECK (residential_status IN ('owned','rented')),
    city                TEXT,
    state               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_applicants_email       ON applicants (email);
CREATE INDEX idx_applicants_pan         ON applicants (pan_number);
CREATE INDEX idx_applicants_name_trgm   ON applicants USING gin (full_name gin_trgm_ops);

-- ── Credit Bureau ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS credit_bureau (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    applicant_id            UUID NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
    credit_score            SMALLINT NOT NULL CHECK (credit_score BETWEEN 300 AND 900),
    total_existing_loans    SMALLINT DEFAULT 0,
    monthly_debt_payments   NUMERIC(14, 2) DEFAULT 0,
    credit_history_years    NUMERIC(5, 1) DEFAULT 0,
    defaults_count          SMALLINT DEFAULT 0,
    enquiries_last_6m       SMALLINT DEFAULT 0,
    score_last_updated      TIMESTAMPTZ DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_credit_bureau_applicant ON credit_bureau (applicant_id);

-- ── Loan Applications ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS loan_applications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    applicant_id        UUID NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
    loan_type           TEXT NOT NULL CHECK (loan_type IN ('home','personal','car','education','business')),
    requested_amount    NUMERIC(16, 2) NOT NULL,
    tenure_years        SMALLINT NOT NULL,
    purpose             TEXT,
    status              TEXT DEFAULT 'pending'
                             CHECK (status IN ('pending','approved','conditional','rejected','disbursed')),
    applied_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at         TIMESTAMPTZ,
    reviewer_notes      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_loan_apps_applicant    ON loan_applications (applicant_id);
CREATE INDEX idx_loan_apps_status       ON loan_applications (status);
CREATE INDEX idx_loan_apps_applied_at   ON loan_applications (applied_at DESC);

-- ── Chat Sessions (for persistent memory) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id      TEXT PRIMARY KEY,
    applicant_id    UUID REFERENCES applicants(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content         TEXT NOT NULL,
    query_type      TEXT,
    confidence      NUMERIC(4,3),
    sources         JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session ON chat_messages (session_id, created_at DESC);

-- ── Row Level Security (Supabase) ────────────────────────────────────────────
ALTER TABLE applicants          ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_bureau       ENABLE ROW LEVEL SECURITY;
ALTER TABLE loan_applications   ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages       ENABLE ROW LEVEL SECURITY;

-- Service role (backend) has full access; anon has none.
CREATE POLICY "service_full_access_applicants"
    ON applicants FOR ALL TO service_role USING (true);
CREATE POLICY "service_full_access_credit"
    ON credit_bureau FOR ALL TO service_role USING (true);
CREATE POLICY "service_full_access_loans"
    ON loan_applications FOR ALL TO service_role USING (true);
CREATE POLICY "service_full_access_sessions"
    ON chat_sessions FOR ALL TO service_role USING (true);
CREATE POLICY "service_full_access_messages"
    ON chat_messages FOR ALL TO service_role USING (true);

-- ── Updated-at trigger ────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

CREATE TRIGGER trg_applicants_updated_at
    BEFORE UPDATE ON applicants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();