from flask import Blueprint, request, jsonify, Response
import os
import sqlite3
import json
import re
import tempfile

bible_bp = Blueprint('bible', __name__)

def ensure_bible_db():
    bible_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'bible.SQLite3')
    db_folder = os.path.dirname(bible_db_path)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
    if not os.path.exists(bible_db_path):
        conn = sqlite3.connect(bible_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                language TEXT,
                abbreviation TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                translation_id INTEGER,
                book_number INTEGER,
                long_name TEXT,
                FOREIGN KEY (translation_id) REFERENCES translations(id)
            )
        """)
        cursor.execute("""
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                translation_id INTEGER,
                name TEXT,
                value TEXT,
                FOREIGN KEY (translation_id) REFERENCES translations(id)
            )
        """)
        conn.commit()
        # Remove year column if exists
        cursor.execute("PRAGMA table_info(info)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'year' in columns:
            # SQLite does not support DROP COLUMN directly, so recreate table
            cursor.execute("ALTER TABLE info RENAME TO info_old")
            cursor.execute("""
                CREATE TABLE info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    translation_id INTEGER,
                    name TEXT,
                    value TEXT,
                    FOREIGN KEY (translation_id) REFERENCES translations(id)
                )
            """)
            cursor.execute("""
                INSERT INTO info (id, translation_id, name, value)
                SELECT id, translation_id, name, value FROM info_old
            """)
            cursor.execute("DROP TABLE info_old")
        conn.commit()
        conn.close()

@bible_bp.route('/api/translations')
def list_translations():
    ensure_bible_db()
    bible_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'bible.SQLite3')
    translations = []
    if os.path.exists(bible_db_path):
        conn = sqlite3.connect(bible_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, language, abbreviation FROM translations")
        for row in cursor.fetchall():
            translation_id, name, language, abbreviation = row
            # Get year from info table (value where name='year')
            cursor.execute("SELECT value FROM info WHERE translation_id=? AND name='year' LIMIT 1", (translation_id,))
            year_row = cursor.fetchone()
            year = year_row[0] if year_row and year_row[0] else ''
            translations.append({
                "name": name,
                "language": language,
                "abbreviation": abbreviation,
                "year": year,
                "filename": None  # No filename, since all are merged into bible.SQLite3
            })
        conn.close()
    return Response(json.dumps({"translations": translations}, ensure_ascii=False), mimetype='application/json')

@bible_bp.route('/api/verses/<translation>')
def load_data(translation):
    ensure_bible_db()
    bible_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'bible.SQLite3')
    conn = sqlite3.connect(bible_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, language, abbreviation FROM translations WHERE name=?", (translation,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify(error=f"Translation '{translation}' not found."), 404
    translation_id, name, language, abbreviation = row
    # Get year from info table
    cursor.execute("SELECT value FROM info WHERE translation_id=? AND name='year' LIMIT 1", (translation_id,))
    year_row = cursor.fetchone()
    year = year_row[0] if year_row and year_row[0] else ''
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
            "Verse": verse_text.strip()
        })
    conn.close()
    return Response(json.dumps({
        "translation": {
            "name": name,
            "language": language,
            "abbreviation": abbreviation,
            "year": year
        },
        "verses": cleaned_rows
    }, ensure_ascii=False), mimetype='application/json')

@bible_bp.route('/api/upload-bible', methods=['POST'])
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
        # Get year from info table if present
        src_cursor.execute("SELECT value FROM info WHERE name='year' LIMIT 1")
        year_row = src_cursor.fetchone()
        src_year = year_row[0] if year_row and year_row[0] else year
        # Get books
        src_cursor.execute("SELECT book_number, long_name FROM books")
        books_data = src_cursor.fetchall()
        # Validate 66 books, Genesis to Revelation, correct order
        expected_books = [
            "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
            "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
            "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
            "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
            "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
            "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
            "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation"
        ]
        books_data_sorted = sorted(books_data, key=lambda x: x[0])
        book_names = [str(b[1]).strip() for b in books_data_sorted]
        # Get verses before validation so it's always defined
        src_cursor.execute("SELECT book_number, chapter, verse, text FROM verses")
        verses_data = src_cursor.fetchall()
        # Get info before validation so it's always defined
        src_cursor.execute("SELECT name, value FROM info")
        info_data = src_cursor.fetchall()
        # If 66 books but not Genesis to Revelation, forcibly set correct names
        if len(book_names) == 66 and book_names != expected_books:
            books_data_sorted = [(i+1, expected_books[i]) for i in range(66)]
            book_names = expected_books.copy()
        # If not 66 books, reject
        if len(book_names) != 66:
            src_conn.close()
            os.remove(tmp_path)
            return jsonify(success=False, error='Uploaded Bible must have exactly 66 books from Genesis to Revelation.'), 400
        src_conn.close()
        os.remove(tmp_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return jsonify(success=False, error=f'Invalid SQLite3 file: {e}'), 400

    # Prepare bible.SQLite3
    bible_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'bible.SQLite3')
    db_folder = os.path.dirname(bible_db_path)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
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
    # Remove year column if exists (for safety, but only needed once)
    bible_cursor.execute("PRAGMA table_info(info)")
    columns = [col[1] for col in bible_cursor.fetchall()]
    if 'year' in columns:
        bible_cursor.execute("ALTER TABLE info RENAME TO info_old")
        bible_cursor.execute("""
            CREATE TABLE info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                translation_id INTEGER,
                name TEXT,
                value TEXT,
                FOREIGN KEY (translation_id) REFERENCES translations(id)
            )
        """)
        bible_cursor.execute("""
            INSERT INTO info (id, translation_id, name, value)
            SELECT id, translation_id, name, value FROM info_old
        """)
        bible_cursor.execute("DROP TABLE info_old")
    bible_conn.commit()
    # Insert or update translation
    bible_cursor.execute("SELECT id FROM translations WHERE name=?", (safe_bible_name,))
    existing = bible_cursor.fetchone()
    if existing:
        translation_id = existing[0]
        # Update abbreviation and language if provided
        bible_cursor.execute("UPDATE translations SET abbreviation=?, language=? WHERE id=?", (src_abbr, language, translation_id))
        # Update year in info table (value only)
        bible_cursor.execute("UPDATE info SET value=? WHERE translation_id=? AND name='year'", (src_year, translation_id))
        bible_cursor.execute("SELECT COUNT(*) FROM info WHERE translation_id=? AND name='year'", (translation_id,))
        if bible_cursor.fetchone()[0] == 0 and src_year:
            bible_cursor.execute("INSERT INTO info (translation_id, name, value) VALUES (?, 'year', ?)", (translation_id, src_year))
    else:
        bible_cursor.execute("INSERT INTO translations (name, language, abbreviation) VALUES (?, ?, ?)", (safe_bible_name, language, src_abbr))
        bible_conn.commit()
        bible_cursor.execute("SELECT id FROM translations WHERE name=?", (safe_bible_name,))
        translation_id = bible_cursor.fetchone()[0]
        if src_year:
            bible_cursor.execute("INSERT INTO info (translation_id, name, value) VALUES (?, 'year', ?)", (translation_id, src_year))
    # Insert books
    bible_cursor.execute("DELETE FROM books WHERE translation_id=?", (translation_id,))
    # Always insert Genesis to Revelation sequence
    for book_number, long_name in books_data_sorted:
        bible_cursor.execute("INSERT INTO books (translation_id, book_number, long_name) VALUES (?, ?, ?)", (translation_id, book_number, long_name))
    # Insert verses
    bible_cursor.execute("DELETE FROM verses WHERE translation_id=?", (translation_id,))
    for book_number, chapter, verse, text in verses_data:
        bible_cursor.execute("INSERT INTO verses (translation_id, book_number, chapter, verse, text) VALUES (?, ?, ?, ?, ?)", (translation_id, book_number, chapter, verse, text))
    # Insert info
    bible_cursor.execute("DELETE FROM info WHERE translation_id=? AND name!='year'", (translation_id,))
    for name, value in info_data:
        if name == 'year':
            continue  # already handled above
        bible_cursor.execute("INSERT INTO info (translation_id, name, value) VALUES (?, ?, ?)", (translation_id, name, value))
    bible_conn.commit()
    bible_conn.close()
    return jsonify(success=True)

@bible_bp.route('/api/update-bible', methods=['POST'])
def update_bible():
    ensure_bible_db()
    old_name = request.form.get('old_name', '').strip()
    new_name = request.form.get('new_name', '').strip()
    new_abbr = request.form.get('new_abbreviation', '').strip()
    new_year = request.form.get('new_year', '').strip()
    file = request.files.get('file')

    if not old_name or not new_name:
        return jsonify(success=False, error='Old name and new name are required.'), 400

    forbidden = r'[\\/:*?"<>|]'
    safe_new_name = re.sub(forbidden, '', new_name).strip()

    bible_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'bible.SQLite3')
    conn = sqlite3.connect(bible_db_path)
    cursor = conn.cursor()
    # Remove year column if exists (for safety, but only needed once)
    cursor.execute("PRAGMA table_info(info)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'year' in columns:
        cursor.execute("ALTER TABLE info RENAME TO info_old")
        cursor.execute("""
            CREATE TABLE info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                translation_id INTEGER,
                name TEXT,
                value TEXT,
                FOREIGN KEY (translation_id) REFERENCES translations(id)
            )
        """)
        cursor.execute("""
            INSERT INTO info (id, translation_id, name, value)
            SELECT id, translation_id, name, value FROM info_old
        """)
        cursor.execute("DROP TABLE info_old")
    conn.commit()

    cursor.execute("SELECT id FROM translations WHERE name=?", (old_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify(success=False, error='Bible not found.'), 404
    translation_id = row[0]

    cursor.execute("UPDATE translations SET name=?, abbreviation=? WHERE id=?", (safe_new_name, new_abbr, translation_id))
    conn.commit()

    # Update year in info table (value only)
    cursor.execute("UPDATE info SET value=? WHERE translation_id=? AND name='year'", (new_year, translation_id))
    cursor.execute("SELECT COUNT(*) FROM info WHERE translation_id=? AND name='year'", (translation_id,))
    if cursor.fetchone()[0] == 0 and new_year:
        cursor.execute("INSERT INTO info (translation_id, name, value) VALUES (?, 'year', ?)", (translation_id, new_year))
    conn.commit()

    # If file is provided, replace books/verses/info for this translation
    if file:
        if file.filename == '' or not (file.filename.lower().endswith('.sqlite3') or file.filename.lower().endswith('.sqlite')):
            conn.close()
            return jsonify(success=False, error='Invalid file type'), 400
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite3') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        try:
            src_conn = sqlite3.connect(tmp_path)
            src_cursor = src_conn.cursor()
            src_cursor.execute("SELECT book_number, long_name FROM books")
            books_data = src_cursor.fetchall()
            src_cursor.execute("SELECT book_number, chapter, verse, text FROM verses")
            verses_data = src_cursor.fetchall()
            src_cursor.execute("SELECT name, value FROM info")
            info_data = src_cursor.fetchall()
            src_conn.close()
            os.remove(tmp_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            conn.close()
            return jsonify(success=False, error=f'Invalid SQLite3 file: {e}'), 400
        # Replace books/verses/info
        cursor.execute("DELETE FROM books WHERE translation_id=?", (translation_id,))
        for book_number, long_name in books_data:
            cursor.execute("INSERT INTO books (translation_id, book_number, long_name) VALUES (?, ?, ?)", (translation_id, book_number, long_name))
        cursor.execute("DELETE FROM verses WHERE translation_id=?", (translation_id,))
        for book_number, chapter, verse, text in verses_data:
            cursor.execute("INSERT INTO verses (translation_id, book_number, chapter, verse, text) VALUES (?, ?, ?, ?, ?)", (translation_id, book_number, chapter, verse, text))
        cursor.execute("DELETE FROM info WHERE translation_id=?", (translation_id,))
        for name, value in info_data:
            if name == 'year':
                cursor.execute("INSERT INTO info (translation_id, name, value) VALUES (?, ?, ?)", (translation_id, name, value))
            else:
                cursor.execute("INSERT INTO info (translation_id, name, value) VALUES (?, ?, ?)", (translation_id, name, value))
        conn.commit()
    conn.close()
    return jsonify(success=True)

@bible_bp.route('/api/delete-bible', methods=['POST'])
def delete_bible():
    ensure_bible_db()
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify(success=False, error='Bible name required.'), 400
    bible_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'bible.SQLite3')
    # Use a short timeout and isolation_level=None for autocommit
    conn = sqlite3.connect(bible_db_path, timeout=10, isolation_level=None)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM translations WHERE name=?", (name,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify(success=False, error='Bible not found.'), 404
        translation_id = row[0]
        # Count translations
        cursor.execute("SELECT COUNT(*) FROM translations")
        count = cursor.fetchone()[0]
        # Only delete books if this is the last translation
        if count == 1:
            cursor.execute("DELETE FROM books WHERE translation_id=?", (translation_id,))
        cursor.execute("DELETE FROM verses WHERE translation_id=?", (translation_id,))
        cursor.execute("DELETE FROM info WHERE translation_id=?", (translation_id,))
        cursor.execute("DELETE FROM translations WHERE id=?", (translation_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify(success=False, error=f'Database error: {e}'), 500
    conn.close()
    return jsonify(success=True)
ensure_bible_db()