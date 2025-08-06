from flask import Blueprint, request, jsonify
import os
import sqlite3
import re
import tempfile
import threading
import json

from routes.bible import STANDARD_BOOKS, ensure_bible_db

upload_bible_bp = Blueprint('upload_bible', __name__)

@upload_bible_bp.route('/api/upload-bible', methods=['POST'])
def upload_bible():
    ensure_bible_db()

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

    # Save uploaded file temporarily
    upload_path = os.path.join(tempfile.gettempdir(), file.filename)
    file.save(upload_path)

    # Validate book count before starting thread
    try:
        conn = sqlite3.connect(upload_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        conn.close()
        if book_count not in (66, 27):
            os.remove(upload_path)
            return jsonify(success=False, error='Uploaded Bible must have exactly 66 books (full) or 27 books (New Testament).'), 400
    except Exception as e:
        if os.path.exists(upload_path):
            os.remove(upload_path)
        return jsonify(success=False, error=f'Invalid SQLite3 file: {e}'), 400

    # Launch background thread to process
    thread = threading.Thread(
        target=process_bible_upload,
        args=(upload_path, bible_name, abbreviation, year)
    )
    thread.start()

    # Return immediately so spinner can hide
    return jsonify(success=True, message="Bible upload started. It will appear shortly.")

def process_bible_upload(file_path, bible_name, abbreviation, year):
    try:
        src_conn = sqlite3.connect(file_path)
        src_cursor = src_conn.cursor()

        # Read data
        language = src_cursor.execute(
            "SELECT value FROM info WHERE name='language' LIMIT 1"
        ).fetchone()
        language = language[0] if language else None

        src_abbr = src_cursor.execute(
            "SELECT value FROM info WHERE name='abbreviation' LIMIT 1"
        ).fetchone()
        src_abbr = src_abbr[0] if src_abbr else abbreviation

        src_year = src_cursor.execute(
            "SELECT value FROM info WHERE name='year' LIMIT 1"
        ).fetchone()
        src_year = src_year[0] if src_year else year

        books_data = src_cursor.execute(
            "SELECT book_number, long_name FROM books ORDER BY book_number"
        ).fetchall()
        # Validate book count again for safety
        if len(books_data) not in (66, 27):
            src_conn.close()
            os.remove(file_path)
            print("Upload failed: must have exactly 66 or 27 books.")
            return
        # Force long_name to standard list
        if len(books_data) == 66:
            books_data = [(num, STANDARD_BOOKS[i]) for i, (num, _) in enumerate(books_data)]
        elif len(books_data) == 27:
            books_data = [(num, STANDARD_BOOKS[i + 39]) for i, (num, _) in enumerate(books_data)]
        verses_data = src_cursor.execute(
            "SELECT book_number, chapter, verse, text FROM verses ORDER BY book_number, chapter, verse"
        ).fetchall()
        info_data = src_cursor.execute("SELECT name, value FROM info").fetchall()

        src_conn.close()
        os.remove(file_path)

        # Insert into main DB
        bible_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'bible.SQLite3')
        conn = sqlite3.connect(bible_db_path, timeout=30)
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO translations (name, language, abbreviation) VALUES (?, ?, ?)",
            (bible_name, language, src_abbr)
        )
        conn.commit()
        translation_id = cur.execute("SELECT last_insert_rowid()").fetchone()[0]

        if src_year:
            cur.execute(
                "INSERT INTO info (translation_id, name, value) VALUES (?, 'year', ?)",
                (translation_id, src_year)
            )

        for name, value in info_data:
            if name != 'year':
                cur.execute(
                    "INSERT INTO info (translation_id, name, value) VALUES (?, ?, ?)",
                    (translation_id, name, value)
                )

        for book_number, long_name in books_data:
            cur.execute(
                "INSERT INTO books (translation_id, book_number, long_name) VALUES (?, ?, ?)",
                (translation_id, book_number, long_name)
            )

        batch_size = 1000
        for i in range(0, len(verses_data), batch_size):
            batch = verses_data[i:i + batch_size]
            cur.executemany(
                "INSERT INTO verses (translation_id, book_number, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
                [(translation_id, b, c, v, t) for (b, c, v, t) in batch]
            )
            conn.commit()

        conn.close()
        print("Bible upload completed.")

    except Exception as e:
        print(f"Error processing Bible upload: {e}")
        conn.close()
        print("Bible upload completed.")

    except Exception as e:
        print(f"Error processing Bible upload: {e}")
