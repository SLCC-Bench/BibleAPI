from flask import Blueprint, request, jsonify
import os
import json

languages_bp = Blueprint('languages', __name__)

LANGUAGES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'languages.json')

def load_languages():
    with open(LANGUAGES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_languages(data):
    with open(LANGUAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@languages_bp.route('/api/languages', methods=['GET'])
def get_languages():
    try:
        return jsonify(load_languages())
    except Exception as e:
        return jsonify(error=str(e)), 500

@languages_bp.route('/api/languages', methods=['POST'])
def upsert_language():
    data = request.get_json()
    code = (data.get('code') or '').strip().lower()
    name = (data.get('name') or '').strip()
    if not code or not name:
        return jsonify(success=False, error='Code and name are required.'), 400
    try:
        languages = load_languages()
        languages[code] = name
        # Keep sorted by code
        languages = dict(sorted(languages.items()))
        save_languages(languages)
        return jsonify(success=True, code=code, name=name)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@languages_bp.route('/api/languages/<code>', methods=['DELETE'])
def delete_language(code):
    code = code.strip().lower()
    try:
        languages = load_languages()
        if code not in languages:
            return jsonify(success=False, error=f"Language code '{code}' not found."), 404
        del languages[code]
        save_languages(languages)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
