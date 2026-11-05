-- Praisehub Database Schema

CREATE TABLE Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    orgname TEXT,
    isregistered INTEGER DEFAULT 0
);

CREATE TABLE Registration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    userid INTEGER NOT NULL,
    registrationkey TEXT NOT NULL,
    FOREIGN KEY(userid) REFERENCES Users(id)
);

-- TiDB/MySQL version (used in production)
CREATE TABLE IF NOT EXISTS RegistrationCodes (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    registration_code VARCHAR(64) NOT NULL,
    registration_type ENUM('trial', 'permanent') NOT NULL,
    expiration_date   DATE NULL,         -- NULL for permanent codes
    is_used           TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_registration_code (registration_code)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;