-- init.sql - uruchamiany automatycznie przy pierwszym starcie kontenera
-- sliplane best practice: /docker-entrypoint-initdb.d/

-- Włącz monitoring zapytań
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Schemat aplikacji
CREATE SCHEMA IF NOT EXISTS app;

-- Tabela użytkowników
CREATE TABLE IF NOT EXISTS app.users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role        VARCHAR(10) NOT NULL CHECK (role IN ('guardian', 'child')),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela parowania urządzeń
CREATE TABLE IF NOT EXISTS app.device_pairs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guardian_id     UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    child_id        UUID REFERENCES app.users(id) ON DELETE SET NULL,
    invite_code     VARCHAR(10) UNIQUE NOT NULL,
    paired_at       TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela lokalizacji
CREATE TABLE IF NOT EXISTS app.locations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id     UUID NOT NULL REFERENCES app.device_pairs(id) ON DELETE CASCADE,
    latitude    DECIMAL(9,6) NOT NULL,
    longitude   DECIMAL(9,6) NOT NULL,
    accuracy    DECIMAL(8,2),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indeks na pair_id + czas - szybkie zapytania "ostatnia lokalizacja"
CREATE INDEX IF NOT EXISTS idx_locations_pair_time
    ON app.locations(pair_id, recorded_at DESC);

-- Tabela wiadomości chat
CREATE TABLE IF NOT EXISTS app.messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id     UUID NOT NULL REFERENCES app.device_pairs(id) ON DELETE CASCADE,
    sender_id   UUID NOT NULL REFERENCES app.users(id),
    content     TEXT NOT NULL,
    sent_at     TIMESTAMPTZ DEFAULT NOW(),
    read_at     TIMESTAMPTZ
);

-- Sesje audio (mikrofon)
CREATE TABLE IF NOT EXISTS app.audio_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id         UUID NOT NULL REFERENCES app.device_pairs(id) ON DELETE CASCADE,
    initiated_by    UUID NOT NULL REFERENCES app.users(id),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE
);
