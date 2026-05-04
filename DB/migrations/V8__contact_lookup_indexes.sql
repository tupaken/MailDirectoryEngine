ALTER TABLE contacts
    ADD COLUMN IF NOT EXISTS normalized_email TEXT;

UPDATE contacts
SET normalized_email = LOWER(BTRIM(email))
WHERE email IS NOT NULL
  AND BTRIM(email) <> ''
  AND normalized_email IS NULL;

CREATE INDEX IF NOT EXISTS ix_contacts_normalized_email
    ON contacts (normalized_email)
    WHERE normalized_email IS NOT NULL;

CREATE TABLE IF NOT EXISTS contact_phone_index (
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    phone_digits TEXT NOT NULL,
    phone_raw TEXT,
    source_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (contact_id, phone_digits, source_key),
    CONSTRAINT contact_phone_index_digits_chk CHECK (BTRIM(phone_digits) <> '')
);

INSERT INTO contact_phone_index (contact_id, phone_digits, phone_raw, source_key)
SELECT c.id,
       REGEXP_REPLACE(phone_value.phone_raw, '\D', '', 'g') AS phone_digits,
       phone_value.phone_raw,
       phone_value.source_key
FROM contacts c
CROSS JOIN LATERAL (
    VALUES
        ('business_phone', c.business_phone),
        ('home_phone', c.home_phone),
        ('mobile_phone', c.mobile_phone),
        ('business_fax', c.business_fax)
) AS phone_value(source_key, phone_raw)
WHERE phone_value.phone_raw IS NOT NULL
  AND BTRIM(phone_value.phone_raw) <> ''
  AND REGEXP_REPLACE(phone_value.phone_raw, '\D', '', 'g') <> ''
ON CONFLICT DO NOTHING;

INSERT INTO contact_phone_index (contact_id, phone_digits, phone_raw, source_key)
SELECT c.id,
       REGEXP_REPLACE(phone_entry.value, '\D', '', 'g') AS phone_digits,
       phone_entry.value AS phone_raw,
       phone_entry.key AS source_key
FROM contacts c
CROSS JOIN LATERAL jsonb_each_text(c.phone_numbers) AS phone_entry(key, value)
WHERE c.phone_numbers IS NOT NULL
  AND c.phone_numbers <> '{}'::jsonb
  AND BTRIM(phone_entry.value) <> ''
  AND REGEXP_REPLACE(phone_entry.value, '\D', '', 'g') <> ''
ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS ix_contact_phone_index_phone_digits
    ON contact_phone_index (phone_digits);
