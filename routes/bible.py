from flask import Blueprint, request, jsonify, Response, send_file
import json
import re

from db import get_db_connection

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


def clean_verse_text_for_response(text):
    if text is None:
        return ""
    cleaned = str(text)
    cleaned = re.sub(r'<S>\d+</S>', '', cleaned)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    cleaned = re.sub(r'\[\s*\d+[a-zA-Z]?†?\s*\]', '', cleaned)
    cleaned = re.sub(r'[\u2460-\u24FF]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


@bible_bp.route('/api/translations')
def list_translations():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, language, abbreviation, year
                FROM translations
                ORDER BY name
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    translations = [
        {
            "name": r["name"],
            "language": r["language"],
            "abbreviation": r["abbreviation"],
            "year": r["year"]
        }
        for r in rows
    ]
    return Response(
        json.dumps({"translations": translations}, ensure_ascii=False),
        mimetype='application/json'
    )


@bible_bp.route('/api/verses/<translation>')
def load_data(translation):
    q = translation.strip().lower()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, language, abbreviation, year
                FROM translations
                WHERE LOWER(name) = %s OR LOWER(abbreviation) = %s
                LIMIT 1
            """, (q, q))
            t_row = cur.fetchone()
            if not t_row:
                return jsonify(error=f"Translation '{translation}' not found."), 404

            cur.execute("""
                SELECT book_name, book_number, sorting_number, chapter, verse_number, text, story_title
                FROM verses
                WHERE translation_id = %s
                ORDER BY book_number, chapter, verse_number
            """, (t_row["id"],))
            verse_rows = cur.fetchall()
    finally:
        conn.close()

    translation_info = {
        "name": t_row["name"],
        "language": t_row["language"],
        "abbreviation": t_row["abbreviation"],
        "year": t_row["year"]
    }

    verses = [
        {
            "Translation": t_row["name"],
            "Reference": f"{v['book_name']} {v['chapter']}:{v['verse_number']}",
            "BookNameSortingOrder": v["book_number"],
            "SortingNumber": v["sorting_number"],
            "BookName": v["book_name"],
            "ChapterNumber": v["chapter"],
            "VerseNumber": v["verse_number"],
            "Verse": clean_verse_text_for_response(v["text"]),
            "StoryTitle": v["story_title"]
        }
        for v in verse_rows
    ]

    return Response(
        json.dumps({"translation": translation_info, "verses": verses}, ensure_ascii=False),
        mimetype='application/json'
    )


@bible_bp.route('/static/db/bible.SQLite3', methods=['GET'])
def download_bible_db():
    return jsonify(error="Bible database not found."), 404


@bible_bp.route('/api/download/bible/zip', methods=['GET'])
def download_bible_zip():
    return jsonify(error="Bible database not found."), 404


@bible_bp.route('/api/books')
def list_books():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM translations ORDER BY name LIMIT 1")
            t = cur.fetchone()
            if not t:
                books_dict = {book: {"chapters": [], "verses": {}} for book in STANDARD_BOOKS}
                return Response(
                    json.dumps({"books": STANDARD_BOOKS, "bookDetails": books_dict}, ensure_ascii=False),
                    mimetype='application/json'
                )
            cur.execute("""
                SELECT book_name, chapter, verse_number
                FROM verses
                WHERE translation_id = %s
                ORDER BY book_number, chapter, verse_number
            """, (t["id"],))
            rows = cur.fetchall()
    finally:
        conn.close()

    books_info = {book: {} for book in STANDARD_BOOKS}
    for v in rows:
        book = v["book_name"]
        chapter = v["chapter"]
        verse = v["verse_number"]
        if book not in books_info:
            books_info[book] = {}
        if chapter not in books_info[book]:
            books_info[book][chapter] = set()
        books_info[book][chapter].add(verse)

    books_dict = {}
    for book in STANDARD_BOOKS:
        chapters = books_info.get(book, {})
        chapters_dict = {str(ch): sorted(list(vv)) for ch, vv in chapters.items()}
        books_dict[book] = {
            "chapters": sorted([int(ch) for ch in chapters_dict.keys()]),
            "verses": chapters_dict
        }
    return Response(
        json.dumps({"books": STANDARD_BOOKS, "bookDetails": books_dict}, ensure_ascii=False),
        mimetype='application/json'
    )


@bible_bp.route('/api/books/<translation>')
def list_books_for_translation(translation):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM translations WHERE LOWER(name) = %s LIMIT 1
            """, (translation.strip().lower(),))
            t = cur.fetchone()
            rows = []
            if t:
                cur.execute("""
                    SELECT book_name, chapter, verse_number
                    FROM verses
                    WHERE translation_id = %s
                    ORDER BY book_number, chapter, verse_number
                """, (t["id"],))
                rows = cur.fetchall()
    finally:
        conn.close()

    books_info = {book: {} for book in STANDARD_BOOKS}
    for v in rows:
        book = v["book_name"]
        chapter = v["chapter"]
        verse = v["verse_number"]
        if book not in books_info:
            books_info[book] = {}
        if chapter not in books_info[book]:
            books_info[book][chapter] = set()
        books_info[book][chapter].add(verse)

    books_dict = {}
    for book in STANDARD_BOOKS:
        chapters = books_info.get(book, {})
        chapters_dict = {str(ch): sorted(list(vv)) for ch, vv in chapters.items()}
        books_dict[book] = {
            "chapters": sorted([int(ch) for ch in chapters_dict.keys()]),
            "verses": chapters_dict
        }
    return Response(
        json.dumps({"books": STANDARD_BOOKS, "bookDetails": books_dict}, ensure_ascii=False),
        mimetype='application/json'
    )


@bible_bp.route('/api/book-structure/<translation>')
def book_structure(translation):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM translations WHERE LOWER(name) = %s LIMIT 1
            """, (translation.strip().lower(),))
            t = cur.fetchone()
            if not t:
                return jsonify(error=f"Translation '{translation}' not found."), 404

            cur.execute("""
                SELECT book_name, book_number, sorting_number, chapter, verse_number
                FROM verses
                WHERE translation_id = %s
                ORDER BY book_number, chapter, verse_number
            """, (t["id"],))
            rows = cur.fetchall()
    finally:
        conn.close()

    book_map = {}
    for v in rows:
        book = v["book_name"]
        bn = v["book_number"]
        sn = v["sorting_number"]
        ch = v["chapter"]
        vn = v["verse_number"]

        if book not in book_map:
            book_map[book] = {
                "BookNameSortingOrder": bn,
                "SortingNumber": sn,
                "BookName": book,
                "chapters": {}
            }
        if ch not in book_map[book]["chapters"]:
            book_map[book]["chapters"][ch] = []
        if vn not in book_map[book]["chapters"][ch]:
            book_map[book]["chapters"][ch].append(vn)

    for book in book_map.values():
        chapters = book["chapters"]
        for ch in chapters:
            chapters[ch] = sorted(chapters[ch])
        book["chapters"] = dict(sorted(chapters.items()))

    sorted_books = sorted(book_map.values(), key=lambda b: b["BookNameSortingOrder"])
    return jsonify({"books": sorted_books})
