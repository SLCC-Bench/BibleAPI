from flask import Blueprint, request, jsonify
import os
import sqlite3
import re
import tempfile
import threading

from routes.bible import STANDARD_BOOKS, ensure_bible_db

update_bible_bp = Blueprint('update_bible', __name__)

@update_bible_bp.route('/api/update-bible', methods=['POST'])
def update_bible():
    ensure_bible_db()

    old_name = request.form.get('old_name', '').strip()
    new_name = request.form.get('new_name', '').strip()
    new_abbr = request.form.get('new_abbreviation', '').strip()
    new_year = request.form.get('new_year', '').strip()
    file = request.files.get('file')

    if not old_name or not new_name:
        return jsonify(success=False, error='Old name and new name are required.'), 400

    # Save uploaded file if provided
    file_path = None
    if file and file.filename and (file.filename.lower().endswith('.sqlite3') or file.filename.lower().endswith('.sqlite')):
        file_path = os.path.join(tempfile.gettempdir(), file.filename)
        file.save(file_path)
        # Validate book count before starting thread
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM books")
            book_count = cursor.fetchone()[0]
            conn.close()
            if book_count not in (66, 27):
                os.remove(file_path)
                return jsonify(success=False, error='Uploaded Bible must have exactly 66 books (full) or 27 books (New Testament).'), 400
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify(success=False, error=f'Invalid SQLite3 file: {e}'), 400

    # Launch background thread for heavy DB work
    thread = threading.Thread(
        target=process_bible_update,
        args=(old_name, new_name, new_abbr, new_year, file_path)
    )
    thread.start()

    return jsonify(success=True, message="Bible update started. Changes will appear shortly.")

def process_bible_update(old_name, new_name, new_abbr, new_year, file_path):
    try:
        bible_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'bible.SQLite3')
        conn = sqlite3.connect(bible_db_path, timeout=30)
        cur = conn.cursor()

        # Find translation to update
        cur.execute("SELECT id FROM translations WHERE name=?", (old_name,))
        row = cur.fetchone()
        if not row:
            print(f"Update failed: Bible '{old_name}' not found.")
            conn.close()
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            return
        translation_id = row[0]

        # Update basic info
        cur.execute("UPDATE translations SET name=?, abbreviation=? WHERE id=?", (new_name, new_abbr, translation_id))
        conn.commit()

        # Update year in info table
        cur.execute("SELECT COUNT(*) FROM info WHERE translation_id=? AND name='year'", (translation_id,))
        exists = cur.fetchone()[0]
        if exists:
            cur.execute("UPDATE info SET value=? WHERE translation_id=? AND name='year'", (new_year, translation_id))
        elif new_year:
            cur.execute("INSERT INTO info (translation_id, name, value) VALUES (?, 'year', ?)", (translation_id, new_year))
        conn.commit()

        # If no file provided, update is done
        if not file_path:
            conn.close()
            return

        # Extract new Bible data
        src_conn = sqlite3.connect(file_path)
        src_cursor = src_conn.cursor()
        books_data = src_cursor.execute("SELECT book_number, long_name FROM books ORDER BY book_number").fetchall()
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
        verses_data = src_cursor.execute("SELECT book_number, chapter, verse, text FROM verses ORDER BY book_number, chapter, verse").fetchall()
        info_data = src_cursor.execute("SELECT name, value FROM info").fetchall()
        src_conn.close()
        os.remove(file_path)

        # Replace old data with new data
        cur.execute("DELETE FROM books WHERE translation_id=?", (translation_id,))
        cur.execute("DELETE FROM verses WHERE translation_id=?", (translation_id,))
        cur.execute("DELETE FROM info WHERE translation_id=?", (translation_id,))
        conn.commit()

        # Insert new info
        if new_year:
            cur.execute("INSERT INTO info (translation_id, name, value) VALUES (?, 'year', ?)", (translation_id, new_year))
        for name, value in info_data:
            if name != 'year':
                cur.execute("INSERT INTO info (translation_id, name, value) VALUES (?, ?, ?)", (translation_id, name, value))

        # Insert new books
        for book_number, long_name in books_data:
            cur.execute("INSERT INTO books (translation_id, book_number, long_name) VALUES (?, ?, ?)", (translation_id, book_number, long_name))

        # Insert new verses in batches to avoid lock
        batch_size = 1000
        for i in range(0, len(verses_data), batch_size):
            batch = verses_data[i:i + batch_size]
            cur.executemany(
                "INSERT INTO verses (translation_id, book_number, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
                [(translation_id, b, c, v, t) for (b, c, v, t) in batch]
            )
            conn.commit()

        conn.close()
        print(f"Bible '{old_name}' updated to '{new_name}' successfully.")

    except Exception as e:
        print(f"Error processing Bible update: {e}")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
