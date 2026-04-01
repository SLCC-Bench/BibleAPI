from flask import Blueprint, request, jsonify, Response, send_file
import os
import sqlite3
import json
import re
import tempfile
import threading
import zipfile

# Standard 66 book names
STANDARD_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation"
]

bible_bp = Blueprint('bible', __name__)

@bible_bp.route('/api/translations')
def list_translations():
    bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
    translations = []
    if os.path.exists(bible_folder):
        for fname in os.listdir(bible_folder):
            if fname.lower().endswith('.json'):
                fpath = os.path.join(bible_folder, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        t = data.get("translation", {})
                        translations.append({
                            "name": t.get("name", ""),
                            "language": t.get("language", ""),
                            "abbreviation": t.get("abbreviation", ""),
                            "year": t.get("year", ""),
                            "filename": fname
                        })
                except Exception:
                    continue
    return Response(json.dumps({"translations": translations}, ensure_ascii=False), mimetype='application/json')

def clean_verse_text_for_response(text):
    if text is None:
        return ""
    cleaned = str(text)
    # Remove Strong's concordance number tags (e.g. <S>7225</S>) before generic tag removal
    cleaned = re.sub(r'<S>\d+</S>', '', cleaned)
    # Remove HTML/XML-like tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    # Remove bracketed footnote markers like [1], [2], [10a], [7†], [ 11 ]
    cleaned = re.sub(r'\[\s*\d+[a-zA-Z]?†?\s*\]', '', cleaned)
    # Remove circled/annotative symbols (e.g., ⓐ ⓑ ... and similar enclosed alphanumerics)
    cleaned = re.sub(r'[\u2460-\u24FF]', '', cleaned)
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

@bible_bp.route('/api/verses/<translation>')
def load_data(translation):
    # Load from JSON file in bible folder
    bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')

    # Try to find the file by matching translation name/abbreviation/filename (case-insensitive)
    json_file = None
    for fname in os.listdir(bible_folder):
        if fname.lower().endswith('.json'):
            fpath = os.path.join(bible_folder, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    t = data.get("translation", {})
                    t_name = (t.get("name", "") or "").strip().lower()
                    t_abbr = (t.get("abbreviation", "") or "").strip().lower()
                    f_stem = os.path.splitext(fname)[0].strip().lower()
                    q = (translation or "").strip().lower()

                    if q in [t_name, t_abbr, f_stem]:
                        json_file = fpath
                        break
            except Exception:
                continue

    if not json_file:
        return jsonify(error=f"Translation '{translation}' not found."), 404

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        translation_info = data.get("translation", {})
        verses = data.get("verses", [])

    # Sanitize Verse text at read-time so old JSON files are also cleaned
    for v in verses:
        if isinstance(v, dict) and "Verse" in v:
            v["Verse"] = clean_verse_text_for_response(v.get("Verse"))

    # Return full verse objects directly from JSON file
    return Response(json.dumps({
        "translation": translation_info,
        "verses": verses
    }, ensure_ascii=False), mimetype='application/json')

@bible_bp.route('/static/db/bible.SQLite3', methods=['GET'])
def download_bible_db():
    return jsonify(error="Bible database not found."), 404

@bible_bp.route('/api/download/bible/zip', methods=['GET'])
def download_bible_zip():
    return jsonify(error="Bible database not found."), 404

@bible_bp.route('/api/books')
def list_books():
    bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
    books_info = {book: {} for book in STANDARD_BOOKS}
    # Find first available translation file
    json_file = None
    for fname in os.listdir(bible_folder):
        if fname.lower().endswith('.json'):
            json_file = os.path.join(bible_folder, fname)
            break
    if json_file:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            verses = data.get("verses", [])
            for v in verses:
                book = v.get("BookName") or v.get("Reference", "").split()[0]
                chapter = v.get("ChapterNumber") or 1
                verse = v.get("VerseNumber") or 1
                if book not in books_info:
                    books_info[book] = {}
                if chapter not in books_info[book]:
                    books_info[book][chapter] = set()
                books_info[book][chapter].add(verse)
    # Convert sets to sorted lists
    books_dict = {}
    for book in STANDARD_BOOKS:
        chapters = books_info.get(book, {})
        chapters_dict = {str(ch): sorted(list(verses)) for ch, verses in chapters.items()}
        books_dict[book] = {
            "chapters": sorted([int(ch) for ch in chapters_dict.keys()]),
            "verses": chapters_dict
        }
    return Response(json.dumps({
        "books": STANDARD_BOOKS,
        "bookDetails": books_dict
    }, ensure_ascii=False), mimetype='application/json')

@bible_bp.route('/api/books/<translation>')
def list_books_for_translation(translation):
    bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
    books_info = {book: {} for book in STANDARD_BOOKS}
    # Find translation file by name
    json_file = None
    for fname in os.listdir(bible_folder):
        if fname.lower().endswith('.json'):
            try:
                with open(os.path.join(bible_folder, fname), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    t = data.get("translation", {})
                    if t.get("name", "").lower() == translation.lower():
                        json_file = os.path.join(bible_folder, fname)
                        break
            except Exception:
                continue
    if json_file:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            verses = data.get("verses", [])
            for v in verses:
                book = v.get("BookName") or v.get("Reference", "").split()[0]
                chapter = v.get("ChapterNumber") or 1
                verse = v.get("VerseNumber") or 1
                if book not in books_info:
                    books_info[book] = {}
                if chapter not in books_info[book]:
                    books_info[book][chapter] = set()
                books_info[book][chapter].add(verse)
    # Convert sets to sorted lists
    books_dict = {}
    for book in STANDARD_BOOKS:
        chapters = books_info.get(book, {})
        chapters_dict = {str(ch): sorted(list(verses)) for ch, verses in chapters.items()}
        books_dict[book] = {
            "chapters": sorted([int(ch) for ch in chapters_dict.keys()]),
            "verses": chapters_dict
        }
    return Response(json.dumps({
        "books": STANDARD_BOOKS,
        "bookDetails": books_dict
    }, ensure_ascii=False), mimetype='application/json')

@bible_bp.route('/api/book-structure/<translation>')
def book_structure(translation):
    bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
    json_file = None
    for fname in os.listdir(bible_folder):
        if fname.lower().endswith('.json'):
            try:
                with open(os.path.join(bible_folder, fname), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    t = data.get("translation", {})
                    if t.get("name", "").lower() == translation.lower():
                        json_file = os.path.join(bible_folder, fname)
                        break
            except Exception:
                continue

    if not json_file:
        return jsonify(error=f"Translation '{translation}' not found."), 404

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        verses = data.get("verses", [])

    # Build structure: {BookName: {BookNameSortingOrder (book_number), SortingNumber, chapters: {chapter: [verse]}}}
    book_map = {}
    sorting_number_map = {}
    current_sorting_number = 1
    # Determine sorting number for each unique BookNameSortingOrder (book_number)
    for v in verses:
        book_number = v.get("BookNameSortingOrder")
        try:
            book_number = int(book_number)
        except (TypeError, ValueError):
            continue
        if book_number not in sorting_number_map:
            sorting_number_map[book_number] = current_sorting_number
            current_sorting_number += 1
    for v in verses:
        book = v.get("BookName")
        book_number = v.get("BookNameSortingOrder")
        chapter = v.get("ChapterNumber")
        verse = v.get("VerseNumber")
        # Ensure chapter and verse are integers for correct sorting and matching
        try:
            chapter = int(chapter)
            verse = int(verse)
            book_number = int(book_number)
        except (TypeError, ValueError):
            continue
        if book is None or book_number is None or chapter is None or verse is None:
            continue
        if book not in book_map:
            book_map[book] = {
                "BookNameSortingOrder": book_number,
                "SortingNumber": sorting_number_map[book_number],
                "BookName": book,
                "chapters": {}
            }
        if chapter not in book_map[book]["chapters"]:
            book_map[book]["chapters"][chapter] = []
        if verse not in book_map[book]["chapters"][chapter]:
            book_map[book]["chapters"][chapter].append(verse)

    # Sort chapters and verses
    for book in book_map.values():
        chapters = book["chapters"]
        for ch in chapters:
            chapters[ch] = sorted(chapters[ch])
        # Ensure chapters are sorted by integer key
        book["chapters"] = dict(sorted(chapters.items(), key=lambda x: x[0]))

    # Sort books by BookNameSortingOrder (book_number)
    sorted_books = sorted(book_map.values(), key=lambda b: b["BookNameSortingOrder"])

    return jsonify({"books": sorted_books})