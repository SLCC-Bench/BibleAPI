-- Additive migration: preserves existing registrations, codes, device IDs and expiry.
-- Run once before deploying hardware-aware clients. Desktop startup never runs this.
ALTER TABLE RegistrationCodes
    ADD COLUMN hardware_device_id CHAR(64) NULL;
ALTER TABLE RegistrationCodes
    ADD UNIQUE KEY uq_hardware_device_id (hardware_device_id);

-- Rollback application code without dropping this nullable column or its bindings.
-- For an idempotent deployment path, use `python app.py --init-db` instead.
