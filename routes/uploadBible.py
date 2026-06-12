from flask import Blueprint, request, jsonify
import os
import sqlite3
import re
import tempfile

from routes.bible import STANDARD_BOOKS
from db import get_db_connection

upload_bible_bp = Blueprint('upload_bible', __name__)


def sanitize_filename(name):
    cleaned = re.sub(r'[^\w\s\-]', '', name, flags=re.UNICODE).strip()
    if not cleaned:
        cleaned = name.encode('utf-8').hex()[:48]
    return cleaned


def clean_verse_text(text):
    if text is None:
        return ""
    cleaned = str(text)
    cleaned = re.sub(r'<S>\d+</S>', '', cleaned)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    cleaned = re.sub(r'\[\s*(?:†?\s*\d+[\d\-:a-zA-Z†]*|#\s*[*†‡§¶]+|¶+)\s*\]', '', cleaned)
    cleaned = re.sub(r'¶+', '', cleaned)
    cleaned = re.sub(r'[\u2460-\u24FF]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Strip KJV marginal notes appended after the verse
    # Handles: Heb., Gr., Cald./Chaldee (Chaldean), Hebr., or,
    match = re.search(r': (?:Heb\.|Gr\.|Cald\.|Chaldee|Chald\.|Chal\.|Hebr\.|or,)', cleaned)
    if match:
        i = match.start() - 1
        while i >= 0 and cleaned[i] not in '.;:,?!':
            i -= 1
        if i >= 0:
            cleaned = cleaned[:i + 1]
    return cleaned


@upload_bible_bp.route('/api/upload-bible', methods=['POST'])
def upload_bible():
    if 'file' not in request.files or 'name' not in request.form:
        return jsonify(success=False, error='File and name are required.'), 400

    file = request.files['file']
    bible_name = request.form['name'].strip()
    abbreviation = request.form.get('abbreviation', '').strip()
    year = request.form.get('year', '').strip()

    if file.filename == '' or not bible_name:
        return jsonify(success=False, error='No selected file or name.'), 400
    if not (file.filename.lower().endswith('.sqlite3') or file.filename.lower().endswith('.sqlite')):
        return jsonify(success=False, error='Invalid file type'), 400

    upload_path = os.path.join(tempfile.gettempdir(), file.filename)
    file.save(upload_path)

    try:
        conn_sqlite = sqlite3.connect(upload_path)
        cursor = conn_sqlite.cursor()

        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        if book_count not in (66, 39, 27):
            conn_sqlite.close()
            os.remove(upload_path)
            return jsonify(success=False, error='Uploaded Bible must have exactly 66, 39, or 27 books.'), 400

        language = cursor.execute(
            "SELECT value FROM info WHERE name='language' LIMIT 1"
        ).fetchone()
        language = language[0] if language else None

        src_abbr = cursor.execute(
            "SELECT value FROM info WHERE name='abbreviation' LIMIT 1"
        ).fetchone()
        src_abbr = src_abbr[0] if src_abbr else abbreviation

        src_year = cursor.execute(
            "SELECT value FROM info WHERE name='year' LIMIT 1"
        ).fetchone()
        src_year = src_year[0] if src_year else year

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
                key = (row[0], row[1], row[2])
                title = row[3]
                # Skip cross-reference entries like "(<x>490 3:23-38</x>)"
                if not title or re.search(r'<x\b', title, re.IGNORECASE):
                    continue
                # Keep only the first readable title per verse key
                if key not in story_titles:
                    story_titles[key] = title
        except Exception:
            pass

        conn_sqlite.close()
        os.remove(upload_path)

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
                None,                   # translation_id — filled in after INSERT
                clean_book,
                book_number,
                sorting_number,
                chapter,
                verse,
                clean_verse_text(text),
                current_story_title
            ))

        # Save to MySQL
        conn_mysql = get_db_connection()
        try:
            with conn_mysql.cursor() as cur:
                cur.execute("SELECT id FROM translations WHERE name = %s", (bible_name,))
                if cur.fetchone():
                    return jsonify(success=False, error=f"Translation '{bible_name}' already exists."), 409

                cur.execute("""
                    INSERT INTO translations (name, language, abbreviation, year)
                    VALUES (%s, %s, %s, %s)
                """, (bible_name, language, src_abbr, src_year))
                translation_id = cur.lastrowid

                # Replace placeholder with real translation_id
                records = [
                    (translation_id, r[1], r[2], r[3], r[4], r[5], r[6], r[7])
                    for r in verse_records
                ]

                chunk_size = 1000
                for i in range(0, len(records), chunk_size):
                    cur.executemany("""
                        INSERT INTO verses
                            (translation_id, book_name, book_number, sorting_number, chapter, verse_number, text, story_title)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, records[i:i + chunk_size])

            conn_mysql.commit()
        finally:
            conn_mysql.close()

        return jsonify(success=True, message="Bible saved to database.")

    except Exception as e:
        if os.path.exists(upload_path):
            os.remove(upload_path)
        return jsonify(success=False, error=f'Error processing Bible: {e}'), 400
