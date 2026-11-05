from flask import Blueprint, request, jsonify

from db import get_db_connection

languages_bp = Blueprint('languages', __name__)


@languages_bp.route('/api/languages', methods=['GET'])
def get_languages():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT code, name FROM languages ORDER BY code")
            rows = cur.fetchall()
    except Exception as e:
        return jsonify(error=str(e)), 500
    finally:
        conn.close()

    return jsonify({r["code"]: r["name"] for r in rows})


@languages_bp.route('/api/languages', methods=['POST'])
def upsert_language():
    data = request.get_json()
    code = (data.get('code') or '').strip().lower()
    name = (data.get('name') or '').strip()
    if not code or not name:
        return jsonify(success=False, error='Code and name are required.'), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO languages (code, name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
            """, (code, name))
        conn.commit()
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

    return jsonify(success=True, code=code, name=name)


@languages_bp.route('/api/languages/<code>', methods=['DELETE'])
def delete_language(code):
    code = code.strip().lower()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT code FROM languages WHERE code = %s", (code,))
            if not cur.fetchone():
                return jsonify(success=False, error=f"Language code '{code}' not found."), 404
            cur.execute("DELETE FROM languages WHERE code = %s", (code,))
        conn.commit()
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

    return jsonify(success=True)
