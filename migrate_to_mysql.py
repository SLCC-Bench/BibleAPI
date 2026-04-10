"""
One-time migration script: Import existing JSON Bible files and languages.json into MySQL.

Usage:
    python migrate_to_mysql.py

Set environment variables before running:
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
"""
import os
import json
import sys

sys.path.insert(0, os.path.dirname(__file__))

from db import get_db_connection, init_db

BIBLE_FOLDER = os.path.join(os.path.dirname(__file__), 'bible')
LANGUAGES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'languages.json')


def migrate_languages(conn):
    if not os.path.exists(LANGUAGES_FILE):
        print("  languages.json not found, skipping.")
        return

    with open(LANGUAGES_FILE, 'r', encoding='utf-8') as f:
        languages = json.load(f)

    with conn.cursor() as cur:
        for code, name in languages.items():
            cur.execute("""
                INSERT INTO languages (code, name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
            """, (code, name))
    conn.commit()
    print(f"  Migrated {len(languages)} languages.")


def migrate_bibles(conn):
    if not os.path.exists(BIBLE_FOLDER):
        print("  bible/ folder not found, skipping.")
        return

    json_files = [f for f in os.listdir(BIBLE_FOLDER) if f.lower().endswith('.json')]
    if not json_files:
        print("  No JSON files found in bible/ folder.")
        return

    for fname in json_files:
        fpath = os.path.join(BIBLE_FOLDER, fname)
        print(f"  Processing {fname}...")

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"    ERROR reading file: {e}")
            continue

        t = data.get("translation", {})
        bible_name = (t.get("name") or "").strip()
        if not bible_name:
            print(f"    SKIP: no translation name.")
            continue

        verses = data.get("verses", [])

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM translations WHERE name = %s", (bible_name,))
            if cur.fetchone():
                print(f"    SKIP: '{bible_name}' already in database.")
                continue

            cur.execute("""
                INSERT INTO translations (name, language, abbreviation, year)
                VALUES (%s, %s, %s, %s)
            """, (bible_name, t.get("language"), t.get("abbreviation"), t.get("year")))
            translation_id = cur.lastrowid

            records = [
                (
                    translation_id,
                    v.get("BookName", ""),
                    v.get("BookNameSortingOrder", 0),
                    v.get("SortingNumber", 0),
                    v.get("ChapterNumber", 0),
                    v.get("VerseNumber", 0),
                    v.get("Verse", ""),
                    v.get("StoryTitle")
                )
                for v in verses
            ]

            chunk_size = 1000
            for i in range(0, len(records), chunk_size):
                cur.executemany("""
                    INSERT INTO verses
                        (translation_id, book_name, book_number, sorting_number, chapter, verse_number, text, story_title)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, records[i:i + chunk_size])

        conn.commit()
        print(f"    Done: '{bible_name}' — {len(verses)} verses inserted.")


def main():
    print("Initializing database schema...")
    init_db()
    print("Schema ready.")

    conn = get_db_connection()
    try:
        print("\nMigrating languages...")
        migrate_languages(conn)

        print("\nMigrating Bible translations...")
        migrate_bibles(conn)
    finally:
        conn.close()

    print("\nMigration complete!")


if __name__ == '__main__':
    main()
