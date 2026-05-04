CREATE TABLE IF NOT EXISTS contact_observations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_key TEXT NOT NULL,
    source_message_id TEXT,
    identity_key TEXT NOT NULL,
    full_name TEXT,
    company_name TEXT,
    email TEXT,
    normalized_email TEXT,
    phone_type TEXT,
    phone_raw TEXT NOT NULL,
    phone_digits TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    reason TEXT,
    seen_count INT NOT NULL DEFAULT 1,
    promoted_contact_ews_id TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT contact_observations_phone_digits_chk CHECK (BTRIM(phone_digits) <> ''),
    CONSTRAINT contact_observations_status_chk CHECK (
        status IN ('pending', 'promoted', 'rejected', 'suspicious')
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_contact_observations_account_identity
    ON contact_observations (account_key, identity_key);

CREATE INDEX IF NOT EXISTS ix_contact_observations_phone_digits
    ON contact_observations (phone_digits);

CREATE INDEX IF NOT EXISTS ix_contact_observations_normalized_email
    ON contact_observations (normalized_email)
    WHERE normalized_email IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_contact_observations_status
    ON contact_observations (status);
