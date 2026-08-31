import os
import pymysql
import pymysql.cursors


def get_db_connection():
    port = int(os.environ.get('MYSQL_PORT', 3306))
    ssl_ca = os.environ.get('MYSQL_SSL_CA')

    kwargs = dict(
        host=os.environ.get('MYSQL_HOST', 'localhost'),
        port=port,
        user=os.environ.get('MYSQL_USER', 'root'),
        password=os.environ.get('MYSQL_PASSWORD', ''),
        database=os.environ.get('MYSQL_DB', 'bibleapi'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

    if ssl_ca:
        kwargs['ssl'] = {'ca': ssl_ca}
    elif os.environ.get('MYSQL_SSL', '').lower() == 'true':
        kwargs['ssl'] = {'ssl_mode': 'VERIFY_IDENTITY'}

    return pymysql.connect(**kwargs)


def init_db():
    """Create all tables if they do not exist (code-first)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS languages (
                    code VARCHAR(10) NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    PRIMARY KEY (code)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(300) NOT NULL,
                    language VARCHAR(100),
                    abbreviation VARCHAR(50),
                    year VARCHAR(20),
                    UNIQUE KEY uq_translation_name (name(191))
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS verses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    translation_id INT NOT NULL,
                    book_name VARCHAR(200) NOT NULL,
                    book_number INT NOT NULL,
                    sorting_number INT NOT NULL,
                    chapter INT NOT NULL,
                    verse_number INT NOT NULL,
                    text MEDIUMTEXT NOT NULL,
                    story_title VARCHAR(1000),
                    FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE CASCADE,
                    INDEX idx_trans_lookup (translation_id, book_number, chapter, verse_number)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS SongDetails (
                    id      INT AUTO_INCREMENT PRIMARY KEY,
                    title   VARCHAR(500),
                    artist  VARCHAR(300),
                    album   VARCHAR(300),
                    genre   VARCHAR(100)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS SongLyrics (
                    id       INT AUTO_INCREMENT PRIMARY KEY,
                    songId   INT,
                    songPart VARCHAR(100),
                    lyrics   MEDIUMTEXT,
                    FOREIGN KEY (songId) REFERENCES SongDetails(id) ON DELETE CASCADE
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS FontSettings (
                    id               INT AUTO_INCREMENT PRIMARY KEY,
                    generalSettingId INT,
                    songId           INT UNIQUE,
                    scriptureId      INT,
                    presentationId   INT,
                    transitionId     INT,
                    fontSize         INT,
                    color            VARCHAR(50),
                    weight           VARCHAR(50),
                    family           VARCHAR(200),
                    outline          VARCHAR(200),
                    shadow           VARCHAR(200),
                    textcase         VARCHAR(50),
                    alignment        VARCHAR(50),
                    bgType           VARCHAR(50),
                    bgImage          TEXT,
                    formattingJson   MEDIUMTEXT,
                    FOREIGN KEY (songId) REFERENCES SongDetails(id) ON DELETE CASCADE
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS RegistrationCodes (
                    id                INT AUTO_INCREMENT PRIMARY KEY,
                    registration_code VARCHAR(128) NOT NULL,
                    registration_type ENUM('trial', 'permanent') NOT NULL,
                    trial_days        INT NULL,
                    expiration_date   DATE NULL,
                    is_used           TINYINT(1) NOT NULL DEFAULT 0,
                    device_id         VARCHAR(255) NULL,
                    UNIQUE KEY uq_registration_code (registration_code(100)),
                    UNIQUE KEY uq_device_id (device_id)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            # Migrations for tables that already existed
            try:
                cur.execute("ALTER TABLE RegistrationCodes ADD COLUMN trial_days INT NULL AFTER registration_type")
                conn.commit()
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE RegistrationCodes MODIFY COLUMN registration_code VARCHAR(128) NOT NULL")
                conn.commit()
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE RegistrationCodes ADD COLUMN device_id VARCHAR(255) NULL")
                conn.commit()
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE RegistrationCodes ADD UNIQUE KEY uq_device_id (device_id)")
                conn.commit()
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()
