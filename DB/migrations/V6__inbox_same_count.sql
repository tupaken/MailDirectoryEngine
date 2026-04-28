ALTER TABLE e_mails_inbox
    ADD COLUMN same_result_count INT NOT NULL DEFAULT 0,
    ADD COLUMN last_result_signature TEXT;