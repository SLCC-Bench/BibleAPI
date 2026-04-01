from flask import Blueprint, request, jsonify
import os
import sqlite3
import re
import tempfile
import json

from routes.bible import STANDARD_BOOKS

upload_bible_bp = Blueprint('upload_bible', __name__)

def sanitize_filename(name):
    # Keep Unicode letters/digits (covers Korean, Japanese, etc.), spaces, hyphens, underscores
    cleaned = re.sub(r'[^\w\s\-]', '', name, flags=re.UNICODE).strip()
    if not cleaned:
        # Fallback: hex-encode the original name so it's always unique and safe
        cleaned = name.encode('utf-8').hex()[:48]
    return cleaned

def clean_verse_text(text):
    if text is None:
        return ""
    cleaned = str(text)
    # Remove Strong's concordance number tags (e.g. <S>7225</S>) before generic tag removal
    cleaned = re.sub(r'<S>\d+</S>', '', cleaned)
    # Remove HTML/XML-like tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    # Remove bracketed footnote markers like [1], [2], [10a], [7†], [ 11 ], [†1-26]
    cleaned = re.sub(r'\[\s*†?\s*\d+[\d\-a-zA-Z†]*\s*\]', '', cleaned)
    # Remove circled/annotative symbols (e.g., ⓐ ⓑ ... and similar enclosed alphanumerics)
    cleaned = re.sub(r'[\u2460-\u24FF]', '', cleaned)
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
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

    # Save uploaded file temporarily
    upload_path = os.path.join(tempfile.gettempdir(), file.filename)
    file.save(upload_path)

    # Validate book count before proceeding
    try:
        conn = sqlite3.connect(upload_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        if book_count not in (66, 39, 27):
            conn.close()
            os.remove(upload_path)
            return jsonify(success=False, error='Uploaded Bible must have exactly 66 books (full), 39 books (Old Testament), or 27 books (New Testament).'), 400

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

        # Get verses with book_number for story linking (use book_number as sorting reference)
        # Check if sorting_order column exists
        cursor.execute("PRAGMA table_info(books)")
        columns = [row[1] for row in cursor.fetchall()]
        # Log all long_name values from books table
        try:
            book_names = cursor.execute("SELECT long_name FROM books ORDER BY book_number").fetchall()
            cleaned_book_names = [row[0].strip() if isinstance(row[0], str) else row[0] for row in book_names]
            print("[UPLOAD BIBLE] Books (long_name):", cleaned_book_names)
        except Exception as e:
            print(f"[UPLOAD BIBLE] Error fetching long_name from books table: {e}")
        if 'sorting_order' in columns:
            verses_data = cursor.execute(
                "SELECT b.book_number, b.sorting_order, b.long_name, v.chapter, v.verse, v.text FROM verses v JOIN books b ON v.book_number = b.book_number"
            ).fetchall()
        else:
            verses_data = cursor.execute(
                "SELECT b.book_number, b.book_number as sorting_order, b.long_name, v.chapter, v.verse, v.text FROM verses v JOIN books b ON v.book_number = b.book_number"
            ).fetchall()
        # Sort verses_data in Python to ensure correct order (cast chapter and verse to int for sorting)
        verses_data = sorted(
            verses_data,
            key=lambda row: (
                int(row[0]),
                int(row[3]) if not isinstance(row[3], int) and str(row[3]).isdigit() else row[3],
                int(row[4]) if not isinstance(row[4], int) and str(row[4]).isdigit() else row[4]
            )
        )

        # Get story titles, keyed by (book_number, chapter, verse)
        story_titles = {}
        try:
            cursor.execute("SELECT book_number, chapter, verse, title FROM stories")
            for row in cursor.fetchall():
                book_number, chapter, verse, title = row
                story_titles[(book_number, chapter, verse)] = title
        except Exception:
            story_titles = {}

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
        last_sorting_order = None
        sorting_number = 0
        current_story_title = None
        for book_number, sorting_order, book, chapter, verse, text in verses_data:
            # Remove leading/trailing whitespace (including newlines) from book name
            clean_book = book.strip() if isinstance(book, str) else book
            # Increment sorting_number only when BookNameSortingOrder changes
            if book_number != last_sorting_order:
                sorting_number += 1
                last_sorting_order = book_number
            reference = f"{clean_book} {chapter}:{verse}"
            # Update current story title if this verse starts a new story section
            story_title = story_titles.get((book_number, chapter, verse))
            if story_title:
                current_story_title = story_title
            verse_entry = {
                "Translation": bible_name,
                "Reference": reference,
                "BookNameSortingOrder": book_number,  # Always use book_number as sorting reference
                "SortingNumber": sorting_number,
                "BookName": clean_book,
                "ChapterNumber": chapter,
                "VerseNumber": verse,
                "Verse": clean_verse_text(text),
                "StoryTitle": current_story_title
            }
            verses.append(verse_entry)

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
