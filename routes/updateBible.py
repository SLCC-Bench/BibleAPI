from flask import Blueprint, request, jsonify
import os
import re
import json
import sqlite3
import tempfile

from routes.uploadBible import clean_verse_text

update_bible_bp = Blueprint('update_bible', __name__)

def sanitize_filename(name):
    # Keep Unicode letters/digits (covers Korean, Japanese, etc.), spaces, hyphens, underscores
    cleaned = re.sub(r'[^\w\s\-]', '', name, flags=re.UNICODE).strip()
    if not cleaned:
        cleaned = name.encode('utf-8').hex()[:48]
    return cleaned

@update_bible_bp.route('/api/update-bible', methods=['POST'])
def update_bible():
    old_name = request.form.get('old_name', '').strip()
    new_name = request.form.get('new_name', '').strip()
    new_abbr = request.form.get('new_abbreviation', '').strip()
    new_year = request.form.get('new_year', '').strip()
    file = request.files.get('file')

    if not old_name or not new_name:
        return jsonify(success=False, error='Old name and new name are required.'), 400

    bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
    old_filename = sanitize_filename(old_name) + ".json"
    old_json_path = os.path.join(bible_folder, old_filename)
    new_filename = sanitize_filename(new_name) + ".json"
    new_json_path = os.path.join(bible_folder, new_filename)

    if not os.path.exists(old_json_path):
        return jsonify(success=False, error=f"Bible '{old_name}' JSON not found."), 404

    upload_path = None
    try:
        if file and file.filename:
            if not (file.filename.lower().endswith('.sqlite3') or file.filename.lower().endswith('.sqlite')):
                return jsonify(success=False, error='Invalid file type. Only .sqlite3 or .sqlite files are accepted.'), 400

            upload_path = os.path.join(tempfile.gettempdir(), file.filename)
            file.save(upload_path)

            conn = sqlite3.connect(upload_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM books")
            book_count = cursor.fetchone()[0]
            if book_count not in (66, 39, 27):
                conn.close()
                raise ValueError('Uploaded Bible must have exactly 66 books (full), 39 books (Old Testament), or 27 books (New Testament).')

            language = cursor.execute("SELECT value FROM info WHERE name='language' LIMIT 1").fetchone()
            language = language[0] if language else None

            src_abbr = cursor.execute("SELECT value FROM info WHERE name='abbreviation' LIMIT 1").fetchone()
            src_abbr = src_abbr[0] if src_abbr else new_abbr

            src_year = cursor.execute("SELECT value FROM info WHERE name='year' LIMIT 1").fetchone()
            src_year = src_year[0] if src_year else new_year

            cursor.execute("PRAGMA table_info(books)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'sorting_order' in columns:
                verses_data = cursor.execute(
                    "SELECT b.book_number, b.sorting_order, b.long_name, v.chapter, v.verse, v.text FROM verses v JOIN books b ON v.book_number = b.book_number"
                ).fetchall()
            else:
                verses_data = cursor.execute(
                    "SELECT b.book_number, b.book_number as sorting_order, b.long_name, v.chapter, v.verse, v.text FROM verses v JOIN books b ON v.book_number = b.book_number"
                ).fetchall()

            verses_data = sorted(
                verses_data,
                key=lambda row: (
                    int(row[0]),
                    int(row[3]) if not isinstance(row[3], int) and str(row[3]).isdigit() else row[3],
                    int(row[4]) if not isinstance(row[4], int) and str(row[4]).isdigit() else row[4]
                )
            )

            story_titles = {}
            try:
                cursor.execute("SELECT book_number, chapter, verse, title FROM stories")
                for row in cursor.fetchall():
                    story_titles[(row[0], row[1], row[2])] = row[3]
            except Exception:
                pass

            conn.close()
            os.remove(upload_path)
            upload_path = None

            translation_info = {
                "name": new_name,
                "language": language,
                "abbreviation": new_abbr if new_abbr else src_abbr,
                "year": new_year if new_year else src_year
            }

            verses = []
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
                verses.append({
                    "Translation": new_name,
                    "Reference": f"{clean_book} {chapter}:{verse}",
                    "BookNameSortingOrder": book_number,
                    "SortingNumber": sorting_number,
                    "BookName": clean_book,
                    "ChapterNumber": chapter,
                    "VerseNumber": verse,
                    "Verse": clean_verse_text(text),
                    "StoryTitle": current_story_title
                })

            bible_json = {"translation": translation_info, "verses": verses}

        else:
            with open(old_json_path, 'r', encoding='utf-8') as f:
                bible_json = json.load(f)

            bible_json["translation"]["name"] = new_name
            if new_abbr:
                bible_json["translation"]["abbreviation"] = new_abbr
            if new_year:
                bible_json["translation"]["year"] = new_year

            for v in bible_json.get("verses", []):
                if "Translation" in v:
                    v["Translation"] = new_name

        with open(new_json_path, 'w', encoding='utf-8') as f:
            json.dump(bible_json, f, ensure_ascii=False, indent=2)

        if old_json_path != new_json_path and os.path.exists(old_json_path):
            os.remove(old_json_path)

        return jsonify(success=True, message=f"Bible '{old_name}' updated to '{new_name}'.", filename=new_filename)

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

    try:
        bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
        filename = sanitize_filename(name) + ".json"
        json_path = os.path.join(bible_folder, filename)
        if os.path.exists(json_path):
            os.remove(json_path)
            return jsonify(success=True, message=f"Bible '{name}' deleted.")
        else:
            return jsonify(success=False, error=f"Bible '{name}' not found."), 404
    except Exception as e:
        return jsonify(success=False, error=f"Error deleting Bible: {e}"), 400
