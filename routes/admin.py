from flask import Blueprint, jsonify, request
from db import get_db_connection
from datetime import date, timedelta
import bcrypt
import hmac
import hashlib
import os
import re

admin_bp = Blueprint('admin', __name__)

_HMAC_SECRET = os.environ.get('HMAC_SECRET', 'praisehub-secret-key').encode('utf-8')

def hash_device_id(device_id):
    return hmac.new(_HMAC_SECRET, device_id.encode('utf-8'), hashlib.sha256).hexdigest()

def is_hashed(value):
    """True if value is already a SHA-256 hex digest (64 lowercase hex chars)."""
    return bool(re.match(r'^[0-9a-f]{64}$', value))


def _lookup_by_device(cur, device_id):
    """
    Look up a RegistrationCodes row by device_id.
    Tries the hashed value first; falls back to plain-text for existing
    unencrypted records and migrates them on the way.
    Returns (row, hashed_device_id).
    """
    hashed = hash_device_id(device_id)

    cur.execute("""
        SELECT id, registration_type, expiration_date
        FROM RegistrationCodes WHERE device_id = %s
    """, (hashed,))
    row = cur.fetchone()
    if row:
        return row, hashed

    # Backward compat: check plain-text device_id (pre-encryption records)
    if not is_hashed(device_id):
        cur.execute("""
            SELECT id, registration_type, expiration_date
            FROM RegistrationCodes WHERE device_id = %s
        """, (device_id,))
        row = cur.fetchone()
        if row:
            # Migrate plain-text device_id to hashed
            cur.execute("UPDATE RegistrationCodes SET device_id = %s WHERE id = %s",
                        (hashed, row['id']))
        return row, hashed

    return None, hashed


@admin_bp.route('/api/registration-codes', methods=['GET'])
def get_registration_codes():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, registration_code, registration_type,
                       trial_days, expiration_date, is_used, device_id
                FROM RegistrationCodes
                ORDER BY id DESC
            """)
            rows = cur.fetchall()
        for row in rows:
            if row.get('expiration_date'):
                row['expiration_date'] = str(row['expiration_date'])
        return jsonify(codes=rows)
    finally:
        conn.close()


@admin_bp.route('/api/registration-codes', methods=['POST'])
def create_registration_code():
    data = request.json or {}
    code = (data.get('registration_code') or '').strip()
    reg_type = data.get('registration_type', '')
    trial_days = data.get('trial_days')

    if not code:
        return jsonify(success=False, error='Registration code is required.'), 400
    if reg_type not in ('trial', 'permanent'):
        return jsonify(success=False, error='Type must be trial or permanent.'), 400
    if reg_type == 'trial' and not trial_days:
        return jsonify(success=False, error='Trial duration is required.'), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO RegistrationCodes (registration_code, registration_type, trial_days)
                VALUES (%s, %s, %s)
            """, (code, reg_type, int(trial_days) if trial_days else None))
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        conn.rollback()
        if 'Duplicate' in str(e) or '1062' in str(e):
            return jsonify(success=False, error='That code already exists.'), 409
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()


@admin_bp.route('/api/registration-codes/<int:code_id>/expire', methods=['POST'])
def expire_registration_code(code_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, registration_type, is_used, expiration_date
                FROM RegistrationCodes WHERE id = %s
            """, (code_id,))
            row = cur.fetchone()

        if not row:
            return jsonify(success=False, error='Registration code not found.'), 404
        if not row['is_used']:
            return jsonify(success=False, error='Code has not been activated yet.'), 400
        if row['registration_type'] == 'permanent':
            return jsonify(success=False, error='Permanent codes cannot be expired.'), 400
        if row['expiration_date'] and date.today() > row['expiration_date']:
            return jsonify(success=False, error='Code is already expired.'), 400

        yesterday = date.today() - timedelta(days=1)
        with conn.cursor() as cur:
            cur.execute("UPDATE RegistrationCodes SET expiration_date = %s WHERE id = %s",
                        (yesterday, code_id))
        conn.commit()
        return jsonify(success=True, expiration_date=str(yesterday))
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()


@admin_bp.route('/api/registration-codes/<int:code_id>', methods=['DELETE'])
def delete_registration_code(code_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM RegistrationCodes WHERE id = %s", (code_id,))
            if not cur.fetchone():
                return jsonify(success=False, error='Registration code not found.'), 404
            cur.execute("DELETE FROM RegistrationCodes WHERE id = %s", (code_id,))
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()


@admin_bp.route('/api/registration-codes/check', methods=['POST'])
def check_registration():
    data = request.json or {}
    device_id = (data.get('device_id') or '').strip()

    if not device_id:
        return jsonify(success=False, error='device_id is required.'), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            row, _ = _lookup_by_device(cur, device_id)
            conn.commit()  # persist any migration update

        if not row:
            return jsonify(registered=False)

        expiration_date = str(row['expiration_date']) if row['expiration_date'] else None
        is_expired = (
            row['registration_type'] == 'trial' and
            row['expiration_date'] is not None and
            date.today() > row['expiration_date']
        )

        return jsonify(
            registered=True,
            registration_type=row['registration_type'],
            expiration_date=expiration_date,
            is_expired=is_expired
        )
    finally:
        conn.close()


@admin_bp.route('/api/registration-codes/redeem', methods=['POST'])
def redeem_registration_code():
    data = request.json or {}
    code = (data.get('registration_code') or '').strip()
    device_id = (data.get('device_id') or '').strip()

    if not code:
        return jsonify(success=False, error='registration_code is required.'), 400
    if not device_id:
        return jsonify(success=False, error='device_id is required.'), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            existing, hashed_device = _lookup_by_device(cur, device_id)
            if existing:
                is_expired_trial = (
                    existing['registration_type'] == 'trial' and
                    existing['expiration_date'] is not None and
                    date.today() > existing['expiration_date']
                )
                if not is_expired_trial:
                    return jsonify(success=False, error='This device already has an active registration.'), 409
                # Expired trial — clear the old binding so the new code can claim this device
                cur.execute("UPDATE RegistrationCodes SET device_id = NULL WHERE id = %s", (existing['id'],))

            cur.execute("""
                SELECT id, registration_type, trial_days, is_used
                FROM RegistrationCodes
                WHERE registration_code = %s
            """, (code,))
            row = cur.fetchone()

        if not row:
            return jsonify(success=False, error='Invalid registration code.'), 404
        if row['is_used']:
            return jsonify(success=False, error='Registration code has already been used.'), 409

        expiration_date = None
        if row['registration_type'] == 'trial':
            days = row['trial_days'] or 7
            expiration_date = date.today() + timedelta(days=days)

        hashed_code = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE RegistrationCodes
                SET is_used = 1, expiration_date = %s, registration_code = %s, device_id = %s
                WHERE id = %s
            """, (expiration_date, hashed_code, hashed_device, row['id']))
        conn.commit()

        return jsonify(
            success=True,
            registration_type=row['registration_type'],
            expiration_date=str(expiration_date) if expiration_date else None
        )
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()
