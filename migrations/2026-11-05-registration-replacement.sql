-- Explicit deployment migration; desktop startup never alters the schema.
ALTER TABLE RegistrationCodes
    ADD COLUMN allow_code_replacement TINYINT(1) NOT NULL DEFAULT 0;
