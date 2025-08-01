from flask import Blueprint, request, jsonify, Response
import os
import sqlite3
import json
import re
import tempfile

bible_bp = Blueprint('bible', __name__)

@bible_bp.route('/api/translations')
def list_translations():
    bible_db_path = os.path.join(os.path.dirname(__file__), 'db', 'bible.SQLite3')
    if not os.path.exists(bible_db_path):
        return Response(json.dumps({"translations": []}, ensure_ascii=False), mimetype='application/json')
    conn = sqlite3.connect(bible_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, language, abbreviation FROM translations")
    translations = []
    for row in cursor.fetchall():
        translations.append({
            "name": row[0],
            "language": row[1],
            "abbreviation": row[2]
        })
    conn.close()
    return Response(json.dumps({"translations": translations}, ensure_ascii=False), mimetype='application/json')

@bible_bp.route('/api/verses/<translation>')
def load_data(translation):
    bible_db_path = os.path.join(os.path.dirname(__file__), 'db', 'bible.SQLite3')
    if not os.path.exists(bible_db_path):
        return jsonify(error=f"Database file not found: {bible_db_path}"), 404
    conn = sqlite3.connect(bible_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, language, abbreviation FROM translations WHERE name=?", (translation,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify(error=f"Translation '{translation}' not found."), 404
    translation_id, language, abbreviation = row
    query = """
        SELECT
            ? AS Translation,
            books.long_name || ' ' || verses.chapter || ':' || verses.verse AS Reference,
            verses.text AS Verse
        FROM verses
        JOIN books ON verses.translation_id = books.translation_id AND verses.book_number = books.book_number
        WHERE verses.translation_id=?
        ORDER BY verses.book_number, CAST(verses.chapter AS INTEGER), CAST(verses.verse AS INTEGER)
    """
    cursor.execute(query, (translation, translation_id))
    rows = cursor.fetchall()
    conn.close()
    cleaned_rows = []
    for row in rows:
        verse_text = row[2] or ''
        # Remove <S> tags with Strong's numbers
        verse_text = re.sub(r'<S>[\d\s,]+<\/S>', '', verse_text)
        # Remove <n>...</n> tags and their contents
        verse_text = re.sub(r'<n>.*?<\/n>', '', verse_text, flags=re.DOTALL)
        # Remove <p ...> tags (including <p> and <p ...>)
        verse_text = re.sub(r'<p[^>]*>', '', verse_text, flags=re.IGNORECASE)
        verse_text = re.sub(r'</p>', '', verse_text, flags=re.IGNORECASE)
        verse_text = re.sub(r'<p[^\s>]*?', '', verse_text, flags=re.IGNORECASE)
        # Remove <pb/> tags
        verse_text = re.sub(r'<pb\s*\/>', '', verse_text, flags=re.IGNORECASE)
        # Remove <i> and </i> tags (including <i ...>)
        verse_text = re.sub(r'</?i[^>]*>', '', verse_text, flags=re.IGNORECASE)
        # Remove custom footnote tags like <f>[7†]</f>
        verse_text = re.sub(r'<f>.*?<\/f>', '', verse_text, flags=re.IGNORECASE)
        # Remove any remaining HTML tags
        verse_text = re.sub(r'<[^>]+>', '', verse_text)
        # Remove leftover raw footnote markers like [7], [8], [10a], [ 11 ]
        verse_text = re.sub(r'\[\s*\d+[a-zA-Z]?†?\s*\]', '', verse_text)
        # Remove unwanted symbols but keep punctuation and letters
        verse_text = re.sub(r'[^\w\s.,;:\'\"!?()\-\–—\[\]{}<>\/]', '', verse_text)
        # Collapse excess whitespace
        verse_text = re.sub(r'\s{2,}', ' ', verse_text)
        cleaned_rows.append({
            "Translation": row[0],
            "Reference": row[1],
            "Verse": verse_text.strip(),
            "Language": language,
            "Abbreviation": abbreviation
        })
    return Response(json.dumps({"verses": cleaned_rows}, ensure_ascii=False), mimetype='application/json')

@bible_bp.route('/api/upload-bible', methods=['POST'])
def upload_bible():
    if 'file' not in request.files or 'name' not in request.form:
        return jsonify(success=False, error='File and name are required.'), 400
    file = request.files['file']
    bible_name = request.form['name'].strip()
    abbreviation = request.form.get('abbreviation', '').strip()
    if file.filename == '' or not bible_name:
        return jsonify(success=False, error='No selected file or name.'), 400
    if not (file.filename.lower().endswith('.sqlite3') or file.filename.lower().endswith('.sqlite')):
        return jsonify(success=False, error='Invalid file type'), 400
    forbidden = r'[\\/:*?"<>|]'
    safe_bible_name = re.sub(forbidden, '', bible_name).strip()
    # Save to a temp file for validation and extraction
    with tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite3') as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    try:
        # Extract data from uploaded bible
        src_conn = sqlite3.connect(tmp_path)
        src_cursor = src_conn.cursor()
        # Get info
        src_cursor.execute("SELECT value FROM info WHERE name='language' LIMIT 1")
        language_row = src_cursor.fetchone()
        language = language_row[0] if language_row and language_row[0] else None
        src_cursor.execute("SELECT value FROM info WHERE name='abbreviation' LIMIT 1")
        abbr_row = src_cursor.fetchone()
        src_abbr = abbr_row[0] if abbr_row and abbr_row[0] else abbreviation
        # Get books
        src_cursor.execute("SELECT book_number, long_name FROM books")
        books_data = src_cursor.fetchall()
        # Get verses
        src_cursor.execute("SELECT book_number, chapter, verse, text FROM verses")
        verses_data = src_cursor.fetchall()
        # Get info table
        src_cursor.execute("SELECT name, value FROM info")
        info_data = src_cursor.fetchall()
        src_conn.close()
        os.remove(tmp_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return jsonify(success=False, error=f'Invalid SQLite3 file: {e}'), 400

    # Prepare bible.SQLite3
    bible_db_path = os.path.join(os.path.dirname(__file__), 'db', 'bible.SQLite3')
    bible_conn = sqlite3.connect(bible_db_path)
    bible_cursor = bible_conn.cursor()
    # Create tables if not exist
    bible_cursor.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            language TEXT,
            abbreviation TEXT
        )
    """)
    bible_cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation_id INTEGER,
            book_number INTEGER,
            long_name TEXT,
            FOREIGN KEY (translation_id) REFERENCES translations(id)
        )
    """)
    bible_cursor.execute("""
        CREATE TABLE IF NOT EXISTS verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation_id INTEGER,
            book_number INTEGER,
            chapter INTEGER,
            verse INTEGER,
            text TEXT,
            FOREIGN KEY (translation_id) REFERENCES translations(id)
        )
    """)
    bible_cursor.execute("""
        CREATE TABLE IF NOT EXISTS info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation_id INTEGER,
            name TEXT,
            value TEXT,
            FOREIGN KEY (translation_id) REFERENCES translations(id)
        )
    """)
    bible_conn.commit()
    # Insert translation
    bible_cursor.execute("INSERT OR IGNORE INTO translations (name, language, abbreviation) VALUES (?, ?, ?)", (safe_bible_name, language, src_abbr))
    bible_conn.commit()
    bible_cursor.execute("SELECT id FROM translations WHERE name=?", (safe_bible_name,))
    translation_id = bible_cursor.fetchone()[0]
    # Insert books
    bible_cursor.execute("DELETE FROM books WHERE translation_id=?", (translation_id,))
    for book_number, long_name in books_data:
        bible_cursor.execute("INSERT INTO books (translation_id, book_number, long_name) VALUES (?, ?, ?)", (translation_id, book_number, long_name))
    # Insert verses
    bible_cursor.execute("DELETE FROM verses WHERE translation_id=?", (translation_id,))
    for book_number, chapter, verse, text in verses_data:
        bible_cursor.execute("INSERT INTO verses (translation_id, book_number, chapter, verse, text) VALUES (?, ?, ?, ?, ?)", (translation_id, book_number, chapter, verse, text))
    # Insert info
    bible_cursor.execute("DELETE FROM info WHERE translation_id=?", (translation_id,))
    for name, value in info_data:
        bible_cursor.execute("INSERT INTO info (translation_id, name, value) VALUES (?, ?, ?)", (translation_id, name, value))
    bible_conn.commit()
    bible_conn.close()
    return jsonify(success=True)
