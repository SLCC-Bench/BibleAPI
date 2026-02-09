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

@bible_bp.route('/api/verses/<translation>')
def load_data(translation):
    # Load from JSON file in bible folder
    bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
    # Try to find the file by matching translation name (case-insensitive, spaces allowed)
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
        translation_info = data.get("translation", {})
        verses = data.get("verses", [])

    # Clean up verse text as in the original code
    cleaned_rows = []
    for v in verses:
        verse_text = v.get("Verse", "")
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
            "Translation": v.get("Translation", ""),
            "Reference": v.get("Reference", ""),
            "Verse": verse_text.strip()
        })

    return Response(json.dumps({
        "translation": {
            "name": translation_info.get("name", ""),
            "language": translation_info.get("language", ""),
            "abbreviation": translation_info.get("abbreviation", ""),
            "year": translation_info.get("year", "")
        },
        "verses": cleaned_rows
    }, ensure_ascii=False), mimetype='application/json')

@bible_bp.route('/static/db/bible.SQLite3', methods=['GET'])
def download_bible_db():
    return jsonify(error="Bible database not found."), 404

@bible_bp.route('/api/download/bible/zip', methods=['GET'])
def download_bible_zip():
    return jsonify(error="Bible database not found."), 404