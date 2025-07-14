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