from flask import Blueprint, request, jsonify
import os
import sqlite3
import re
import tempfile
import json

from routes.bible import STANDARD_BOOKS, ensure_bible_db

upload_bible_bp = Blueprint('upload_bible', __name__)

def sanitize_filename(name):
    # Remove unsafe characters for filenames, but allow spaces
    return re.sub(r'[^a-zA-Z0-9_\- ]', '', name)

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

    # Validate book count before proceeding
    try:
        conn = sqlite3.connect(upload_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        if book_count not in (66, 27):
            conn.close()
            os.remove(upload_path)
            return jsonify(success=False, error='Uploaded Bible must have exactly 66 books (full) or 27 books (New Testament).'), 400

        # Gather translation info
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

        # Get verses
        verses_data = cursor.execute(
            "SELECT b.long_name, v.chapter, v.verse, v.text FROM verses v JOIN books b ON v.book_number = b.book_number ORDER BY v.book_number, v.chapter, v.verse"
        ).fetchall()

        conn.close()
        os.remove(upload_path)

        # Prepare JSON structure
        translation_info = {
            "name": bible_name,
            "language": language,
            "abbreviation": src_abbr,
            "year": src_year
        }
        verses = []
        for book, chapter, verse, text in verses_data:
            reference = f"{book} {chapter}:{verse}"
            verses.append({
                "Translation": bible_name,
                "Reference": reference,
                "Verse": text
            })

        bible_json = {
            "translation": translation_info,
            "verses": verses
        }

        # Save to bible folder
        bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
        os.makedirs(bible_folder, exist_ok=True)
        filename = sanitize_filename(bible_name) + ".json"
        json_path = os.path.join(bible_folder, filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(bible_json, f, ensure_ascii=False, indent=2)

        return jsonify(success=True, message="Bible JSON saved.", filename=filename)

    except Exception as e:
        if os.path.exists(upload_path):
            os.remove(upload_path)
        return jsonify(success=False, error=f'Error processing Bible: {e}'), 400
