-- Persist contacts derived from ContactService canonical payload / EWS mapping.
CREATE TABLE IF NOT EXISTS contacts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_message_id TEXT,
    display_name TEXT NOT NULL,
    full_name TEXT,
    given_name TEXT,
    middle_name TEXT,
    surname TEXT,
    company_name TEXT,
    job_title TEXT,
    file_as TEXT,
    email TEXT,
    website TEXT,
    business_phone TEXT,
    home_phone TEXT,
    mobile_phone TEXT,
    business_fax TEXT,
    street TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country_or_region TEXT,
    postal_address_index TEXT,
    notes TEXT,
    emails JSONB NOT NULL DEFAULT '{}'::jsonb,
    phone_numbers JSONB NOT NULL DEFAULT '{}'::jsonb,
    addresses JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT contacts_name_present_chk CHECK (
        COALESCE(
            NULLIF(BTRIM(full_name), ''),
            NULLIF(BTRIM(given_name), ''),
            NULLIF(BTRIM(surname), ''),
            NULLIF(BTRIM(display_name), '')
        ) IS NOT NULL
    ),
    CONSTRAINT contacts_phone_present_chk CHECK (
        COALESCE(
            NULLIF(BTRIM(business_phone), ''),
            NULLIF(BTRIM(mobile_phone), ''),
            NULLIF(BTRIM(home_phone), ''),
            NULLIF(BTRIM(business_fax), '')
        ) IS NOT NULL
        OR phone_numbers <> '{}'::jsonb
    )
);

CREATE INDEX IF NOT EXISTS ix_contacts_created_at
    ON contacts (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_contacts_source_message_id
    ON contacts (source_message_id);
