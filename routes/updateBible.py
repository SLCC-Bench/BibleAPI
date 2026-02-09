from flask import Blueprint, request, jsonify
import os
import re
import json

update_bible_bp = Blueprint('update_bible', __name__)

def sanitize_filename(name):
    # Remove unsafe characters for filenames, but allow spaces
    return re.sub(r'[^a-zA-Z0-9_\- ]', '', name)

@update_bible_bp.route('/api/update-bible', methods=['POST'])
def update_bible():
    old_name = request.form.get('old_name', '').strip()
    new_name = request.form.get('new_name', '').strip()
    new_abbr = request.form.get('new_abbreviation', '').strip()
    new_year = request.form.get('new_year', '').strip()
    file = request.files.get('file')

    if not old_name or not new_name:
        return jsonify(success=False, error='Old name and new name are required.'), 400

    if file and file.filename:
        return jsonify(success=False, error='File upload not supported for JSON update.'), 400

    try:
        bible_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bible')
        old_filename = sanitize_filename(old_name) + ".json"
        old_json_path = os.path.join(bible_folder, old_filename)
        new_filename = sanitize_filename(new_name) + ".json"
        new_json_path = os.path.join(bible_folder, new_filename)

        if not os.path.exists(old_json_path):
            return jsonify(success=False, error=f"Bible '{old_name}' JSON not found."), 404

        # Load, update, and save JSON
        with open(old_json_path, 'r', encoding='utf-8') as f:
            bible_json = json.load(f)

        # Update translation fields
        if "translation" in bible_json:
            bible_json["translation"]["name"] = new_name
            if new_abbr:
                bible_json["translation"]["abbreviation"] = new_abbr
            if new_year:
                bible_json["translation"]["year"] = new_year

        # Update all verse "Translation" fields if present
        if "verses" in bible_json:
            for v in bible_json["verses"]:
                if "Translation" in v:
                    v["Translation"] = new_name

        # Save to new file (overwrite if same name)
        with open(new_json_path, 'w', encoding='utf-8') as f:
            json.dump(bible_json, f, ensure_ascii=False, indent=2)

        # Remove old file if name changed
        if old_json_path != new_json_path:
            os.remove(old_json_path)

        return jsonify(success=True, message=f"Bible '{old_name}' updated to '{new_name}'.", filename=new_filename)
    except Exception as e:
        return jsonify(success=False, error=f"Error updating Bible JSON: {e}"), 400
