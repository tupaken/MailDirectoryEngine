-- Fix oversized index entries caused by UNIQUE constraint on large TEXT content.
-- Also align deduplication constraints with application logic (hash scoped by account).

ALTER TABLE e_mails_inbox
DROP CONSTRAINT IF EXISTS e_mails_inbox_content_key;

ALTER TABLE e_mails_inbox
DROP CONSTRAINT IF EXISTS e_mails_inbox_hash_key;

ALTER TABLE e_mails_send
DROP CONSTRAINT IF EXISTS e_mails_send_hash_key;

ALTER TABLE e_mails_inbox
ADD CONSTRAINT e_mails_inbox_hash_account_key UNIQUE (hash, account);

ALTER TABLE e_mails_send
ADD CONSTRAINT e_mails_send_hash_account_key UNIQUE (hash, account);
