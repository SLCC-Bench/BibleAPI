from flask import Flask, jsonify
import sqlite3
import os
import re

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    db_folder = os.path.join(os.path.dirname(__file__), 'db', 'bibles')
    db_files = [f for f in os.listdir(db_folder) if f.endswith('.SQLite3')]
    result = {}

    for db_file in db_files:
        db_path = os.path.join(db_folder, db_file)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users")
            rows = cursor.fetchall()
            conn.close()
            result[db_file] = [{"id": row[0], "name": row[1]} for row in rows]
        except Exception:
            result[db_file] = []

    return jsonify(users=result)

@app.route('/api/translations')
def list_translations():
    db_folder = os.path.join(os.path.dirname(__file__), 'db', 'bibles')
    if not os.path.exists(db_folder):
        # Folder does not exist, return empty list
        return jsonify(translations=[])
    files = [f for f in os.listdir(db_folder) if f.endswith('.SQLite3')]
    translations = []
    for f in files:
        translation_name = f.replace('.SQLite3', '')
        db_path = os.path.join(db_folder, f)
        language = None
        try:
            conn = sqlite3.connect(db_path)
            print(f"Successfully connected to database: {db_path}")
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM info WHERE name='language' LIMIT 1")
            row = cursor.fetchone()
            print(f"Row fetched from info table (language): {row}")
            if row and row[0]:
                language = row[0]
            conn.close()
        except Exception as e:
            print(f"Exception for {translation_name}: {e}")
            language = None
        print(f"Translation: {translation_name}, Language: {language}")
        translations.append({
            "name": translation_name,
            "language": language
        })
    return jsonify(translations=translations)

@app.route('/api/verses/<translation>')
def load_data(translation):
    db_folder = os.path.join(os.path.dirname(__file__), 'db', 'bibles')
    db_path = os.path.join(db_folder, f"{translation}.SQLite3")
    if not os.path.exists(db_path):
        return jsonify(error=f"Database file not found: {db_path}"), 404

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = """
        SELECT
            ? AS Translation,
            books.long_name || ' ' || verses.chapter || ':' || verses.verse AS Reference,
            verses.text AS Verse
        FROM verses
        JOIN books ON verses.book_number = books.book_number
        ORDER BY verses.book_number, verses.chapter, verses.verse
    """
    cursor.execute(query, (translation,))
    rows = cursor.fetchall()
    conn.close()

    cleaned_rows = []
    for row in rows:
        verse_text = row[2]
        # Remove <S> tags with Strong's numbers
        verse_text = re.sub(r'<S>[\d\s,]+<\/S>', '', verse_text)
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

    return jsonify(verses=cleaned_rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
