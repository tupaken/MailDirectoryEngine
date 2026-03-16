ALTER TABLE e_mails_send
ADD account TEXT ;

UPDATE e_mails_send
SET account = 'bewerbung';

ALTER TABLE e_mails_send
ALTER COLUMN account SET NOT NULL;

ALTER TABLE e_mails_inbox
ADD account TEXT;

UPDATE e_mails_inbox
SET account = 'bewerbung';

ALTER TABLE e_mails_inbox
ALTER COLUMN account SET NOT NULL;