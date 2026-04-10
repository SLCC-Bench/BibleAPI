from flask import Blueprint, request, jsonify
import os
import re
import sqlite3
import tempfile

from routes.uploadBible import clean_verse_text
from db import get_db_connection

update_bible_bp = Blueprint('update_bible', __name__)


@update_bible_bp.route('/api/update-bible', methods=['POST'])
def update_bible():
    old_name = request.form.get('old_name', '').strip()
    new_name = request.form.get('new_name', '').strip()
    new_abbr = request.form.get('new_abbreviation', '').strip()
    new_year = request.form.get('new_year', '').strip()
    file = request.files.get('file')

    if not old_name or not new_name:
        return jsonify(success=False, error='Old name and new name are required.'), 400

    conn_mysql = get_db_connection()
    try:
        with conn_mysql.cursor() as cur:
            cur.execute("SELECT id FROM translations WHERE name = %s", (old_name,))
            row = cur.fetchone()
            if not row:
                return jsonify(success=False, error=f"Translation '{old_name}' not found."), 404
            translation_id = row["id"]
    finally:
        conn_mysql.close()

    upload_path = None
    try:
        if file and file.filename:
            if not (file.filename.lower().endswith('.sqlite3') or file.filename.lower().endswith('.sqlite')):
                return jsonify(success=False, error='Invalid file type. Only .sqlite3 or .sqlite files are accepted.'), 400

            upload_path = os.path.join(tempfile.gettempdir(), file.filename)
            file.save(upload_path)

            conn_sqlite = sqlite3.connect(upload_path)
            cursor = conn_sqlite.cursor()

            cursor.execute("SELECT COUNT(*) FROM books")
            book_count = cursor.fetchone()[0]
            if book_count not in (66, 39, 27):
                conn_sqlite.close()
                raise ValueError('Uploaded Bible must have exactly 66, 39, or 27 books.')

            language = cursor.execute(
                "SELECT value FROM info WHERE name='language' LIMIT 1"
            ).fetchone()
            language = language[0] if language else None

            src_abbr = cursor.execute(
                "SELECT value FROM info WHERE name='abbreviation' LIMIT 1"
            ).fetchone()
            src_abbr = src_abbr[0] if src_abbr else new_abbr

            src_year = cursor.execute(
                "SELECT value FROM info WHERE name='year' LIMIT 1"
            ).fetchone()
            src_year = src_year[0] if src_year else new_year

            cursor.execute("PRAGMA table_info(books)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'sorting_order' in columns:
                verses_data = cursor.execute(
                    "SELECT b.book_number, b.sorting_order, b.long_name, v.chapter, v.verse, v.text "
                    "FROM verses v JOIN books b ON v.book_number = b.book_number"
                ).fetchall()
            else:
                verses_data = cursor.execute(
                    "SELECT b.book_number, b.book_number as sorting_order, b.long_name, v.chapter, v.verse, v.text "
                    "FROM verses v JOIN books b ON v.book_number = b.book_number"
                ).fetchall()

            verses_data = sorted(
                verses_data,
                key=lambda row: (
                    int(row[0]),
                    int(row[3]) if str(row[3]).isdigit() else row[3],
                    int(row[4]) if str(row[4]).isdigit() else row[4]
                )
            )

            story_titles = {}
            try:
                cursor.execute("SELECT book_number, chapter, verse, title FROM stories")
                for row in cursor.fetchall():
                    story_titles[(row[0], row[1], row[2])] = row[3]
            except Exception:
                pass

            conn_sqlite.close()
            os.remove(upload_path)
            upload_path = None

            # Build verse records
            verse_records = []
            last_book_number = None
            sorting_number = 0
            current_story_title = None

            for book_number, sorting_order, book, chapter, verse, text in verses_data:
                clean_book = book.strip() if isinstance(book, str) else book
                if book_number != last_book_number:
                    sorting_number += 1
                    last_book_number = book_number
                story_title = story_titles.get((book_number, chapter, verse))
                if story_title:
                    current_story_title = story_title
                verse_records.append((
                    translation_id,
                    clean_book,
                    book_number,
                    sorting_number,
                    chapter,
                    verse,
                    clean_verse_text(text),
                    current_story_title
                ))

            conn_mysql = get_db_connection()
            try:
                with conn_mysql.cursor() as cur:
                    # Update translation metadata
                    cur.execute("""
                        UPDATE translations
                        SET name = %s,
                            language = %s,
                            abbreviation = %s,
                            year = %s
                        WHERE id = %s
                    """, (
                        new_name,
                        language,
                        new_abbr if new_abbr else src_abbr,
                        new_year if new_year else src_year,
                        translation_id
                    ))

                    # Replace all verses
                    cur.execute("DELETE FROM verses WHERE translation_id = %s", (translation_id,))

                    chunk_size = 1000
                    for i in range(0, len(verse_records), chunk_size):
                        cur.executemany("""
                            INSERT INTO verses
                                (translation_id, book_name, book_number, sorting_number, chapter, verse_number, text, story_title)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, verse_records[i:i + chunk_size])

                conn_mysql.commit()
            finally:
                conn_mysql.close()

        else:
            # Metadata-only update (no new file)
            conn_mysql = get_db_connection()
            try:
                with conn_mysql.cursor() as cur:
                    fields = ["name = %s"]
                    values = [new_name]
                    if new_abbr:
                        fields.append("abbreviation = %s")
                        values.append(new_abbr)
                    if new_year:
                        fields.append("year = %s")
                        values.append(new_year)
                    values.append(translation_id)
                    cur.execute(
                        f"UPDATE translations SET {', '.join(fields)} WHERE id = %s",
                        values
                    )
                conn_mysql.commit()
            finally:
                conn_mysql.close()

        return jsonify(success=True, message=f"Bible '{old_name}' updated to '{new_name}'.")

    except ValueError as e:
        if upload_path and os.path.exists(upload_path):
            os.remove(upload_path)
        return jsonify(success=False, error=str(e)), 400
    except Exception as e:
        if upload_path and os.path.exists(upload_path):
            os.remove(upload_path)
        return jsonify(success=False, error=f"Error updating Bible: {e}"), 400


@update_bible_bp.route('/api/delete-bible', methods=['POST'])
def delete_bible():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify(success=False, error='Bible name is required.'), 400

    conn_mysql = get_db_connection()
    try:
        with conn_mysql.cursor() as cur:
            cur.execute("SELECT id FROM translations WHERE name = %s", (name,))
            row = cur.fetchone()
            if not row:
                return jsonify(success=False, error=f"Translation '{name}' not found."), 404
            # Verses are removed via ON DELETE CASCADE
            cur.execute("DELETE FROM translations WHERE id = %s", (row["id"],))
        conn_mysql.commit()
    except Exception as e:
        return jsonify(success=False, error=f"Error deleting Bible: {e}"), 400
    finally:
        conn_mysql.close()

    return jsonify(success=True, message=f"Bible '{name}' deleted.")
