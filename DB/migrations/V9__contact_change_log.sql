CREATE TABLE IF NOT EXISTS contact_change_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
    ews_id TEXT,
    observation_id BIGINT REFERENCES contact_observations(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    source_message_id TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT contact_change_log_action_chk CHECK (
        action IN ('created', 'updated', 'unchanged', 'pending', 'suspicious', 'rejected')
    )
);

CREATE INDEX IF NOT EXISTS ix_contact_change_log_contact_id
    ON contact_change_log (contact_id);

CREATE INDEX IF NOT EXISTS ix_contact_change_log_observation_id
    ON contact_change_log (observation_id);

CREATE INDEX IF NOT EXISTS ix_contact_change_log_created_at
    ON contact_change_log (created_at DESC);
