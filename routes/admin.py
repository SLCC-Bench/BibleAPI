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

def normalize_device_id(device_id):
    return device_id.strip().lower()

def hash_device_id(device_id):
    normalized = normalize_device_id(device_id)
    return hmac.new(_HMAC_SECRET, normalized.encode('utf-8'), hashlib.sha256).hexdigest()

def is_hashed(value):
    """True if value is already a SHA-256 hex digest (64 lowercase hex chars)."""
    return bool(re.match(r'^[0-9a-f]{64}$', value))


class HardwareBindingConflict(ValueError):
    pass


def hash_hardware_id(hardware_id):
    return hmac.new(_HMAC_SECRET, b'praisehub:hardware:v1\0' + hardware_id.encode('ascii'), hashlib.sha256).hexdigest()


def _expired(row):
    return (row['registration_type'] == 'trial' and row['expiration_date'] is not None
            and date.today() > row['expiration_date'])


def _same_code(code, stored):
    if stored.startswith(('$2a$', '$2b$', '$2y$')):
        try:
            return bcrypt.checkpw(code.encode('utf-8'), stored.encode('utf-8'))
        except ValueError:
            return False
    return hmac.compare_digest(code.encode('utf-8'), stored.encode('utf-8'))


def _lookup_identity(cur, device_id, hardware_id):
    hashed_device = hash_device_id(device_id) if device_id else None
    hashed_hardware = hash_hardware_id(hardware_id) if hardware_id else None
    if hashed_hardware:
        cur.execute("""
            SELECT id, registration_type, expiration_date, registration_code, is_used, hardware_device_id
            FROM RegistrationCodes WHERE hardware_device_id = %s FOR UPDATE
        """, (hashed_hardware,))
        row = cur.fetchone()
        if row:
            return row, hashed_device, hashed_hardware
    row, _ = _lookup_by_device(cur, device_id) if device_id else (None, None)
    if row and hashed_hardware:
        cur.execute("""
            SELECT id, registration_type, expiration_date, registration_code, is_used, hardware_device_id, device_id
            FROM RegistrationCodes WHERE id = %s FOR UPDATE
        """, (row['id'],))
        row = cur.fetchone()
        if not row:
            return None, hashed_device, hashed_hardware
        if row['device_id'] not in (hashed_device, device_id):
            raise HardwareBindingConflict('Registration device binding changed. Retry activation.')
        if row['hardware_device_id'] and row['hardware_device_id'] != hashed_hardware:
            raise HardwareBindingConflict('Registration is bound to another physical device.')
    return row, hashed_device, hashed_hardware


def _bind_hardware(cur, row, hashed_hardware):
    if not hashed_hardware or row.get('hardware_device_id') == hashed_hardware:
        return
    cur.execute("""
        UPDATE RegistrationCodes SET hardware_device_id = %s
        WHERE id = %s AND hardware_device_id IS NULL
    """, (hashed_hardware, row['id']))
    if cur.rowcount == 0:
        cur.execute("SELECT hardware_device_id FROM RegistrationCodes WHERE id = %s FOR UPDATE", (row['id'],))
        current = cur.fetchone()
        if not current or current['hardware_device_id'] != hashed_hardware:
            raise HardwareBindingConflict('Registration hardware binding changed. Retry activation.')


def _registration_error(conn, error):
    conn.rollback()
    if isinstance(error, HardwareBindingConflict) or (error.args and error.args[0] == 1062):
        return jsonify(success=False, error='Registration is bound to another physical device.'), 409
    if error.args and error.args[0] == 1054:
        return jsonify(success=False, error='Hardware registration requires a database migration. Run BibleAPI --init-db before using hardware identities.'), 503
    return jsonify(success=False, error='Registration could not be verified. Please retry.'), 500


def _lookup_by_device(cur, device_id):
    """
    Look up a RegistrationCodes row by device_id.
    Tries the hashed value first; falls back to plain-text for existing
    unencrypted records and migrates them on the way.
    Returns (row, hashed_device_id).
    """
    hashed = hash_device_id(device_id)

    cur.execute("""
        SELECT id, registration_type, expiration_date, registration_code, is_used
        FROM RegistrationCodes WHERE device_id = %s
    """, (hashed,))
    row = cur.fetchone()
    if row:
        return row, hashed

    # Backward compat: check plain-text device_id (pre-encryption records)
    if not is_hashed(device_id):
        cur.execute("""
            SELECT id, registration_type, expiration_date, registration_code, is_used
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
    hardware_id = data.get('hardware_id') or ''
    if not isinstance(hardware_id, str) or (hardware_id and not re.fullmatch(r'[0-9a-fA-F]{64}', hardware_id)):
        return jsonify(success=False, error='hardware_id must be a SHA-256 identity.'), 400
    hardware_id = hardware_id.lower()

    if not device_id and not hardware_id:
        return jsonify(success=False, error='A device identity is required.'), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            row, _, hashed_hardware = _lookup_identity(cur, device_id, hardware_id)
            if row and row['is_used'] and not _expired(row):
                _bind_hardware(cur, row, hashed_hardware)
            conn.commit()  # persist any migration update

        if not row or not row['is_used']:
            return jsonify(registered=False)

        expiration_date = str(row['expiration_date']) if row['expiration_date'] else None
        is_expired = _expired(row)

        return jsonify(
            registered=True,
            registration_type=row['registration_type'],
            expiration_date=expiration_date,
            is_expired=is_expired
        )
    except Exception as error:
        return _registration_error(conn, error)
    finally:
        conn.close()


@admin_bp.route('/api/registration-codes/redeem', methods=['POST'])
def redeem_registration_code():
    data = request.json or {}
    code = (data.get('registration_code') or '').strip()
    device_id = (data.get('device_id') or '').strip()
    hardware_id = data.get('hardware_id') or ''
    if not isinstance(hardware_id, str) or (hardware_id and not re.fullmatch(r'[0-9a-fA-F]{64}', hardware_id)):
        return jsonify(success=False, error='hardware_id must be a SHA-256 identity.'), 400
    hardware_id = hardware_id.lower()

    if not code:
        return jsonify(success=False, error='registration_code is required.'), 400
    if not device_id and not hardware_id:
        return jsonify(success=False, error='A device identity is required.'), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            existing, hashed_device, hashed_hardware = _lookup_identity(cur, device_id, hardware_id)
            if existing:
                is_expired_trial = _expired(existing)
                if existing['is_used'] and _same_code(code, existing['registration_code']):
                    if is_expired_trial:
                        return jsonify(success=False, error='Registration code has expired.'), 403
                    _bind_hardware(cur, existing, hashed_hardware)
                    conn.commit()  # Persist any legacy device-ID migration.
                    return jsonify(
                        success=True,
                        registration_type=existing['registration_type'],
                        expiration_date=str(existing['expiration_date']) if existing['expiration_date'] else None
                    )
                if not is_expired_trial:
                    return jsonify(success=False, error='This device already has an active registration.'), 409

            cur.execute("""
                SELECT id, registration_type, trial_days, is_used
                FROM RegistrationCodes
                WHERE registration_code = %s FOR UPDATE
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

        with conn.cursor() as cur:
            if existing:
                # Old clients can renew an expired trial without losing its hardware link.
                if not hashed_hardware:
                    try:
                        cur.execute("SELECT hardware_device_id FROM RegistrationCodes WHERE id = %s FOR UPDATE", (existing['id'],))
                        hashed_hardware = cur.fetchone()['hardware_device_id']
                    except Exception as error:
                        if not error.args or error.args[0] != 1054:
                            raise
                if hashed_hardware:
                    cur.execute("UPDATE RegistrationCodes SET device_id = NULL, hardware_device_id = NULL WHERE id = %s", (existing['id'],))
                else:
                    cur.execute("UPDATE RegistrationCodes SET device_id = NULL WHERE id = %s", (existing['id'],))
            cur.execute("""
                UPDATE RegistrationCodes
                SET is_used = 1, expiration_date = %s, device_id = %s
                WHERE id = %s AND is_used = 0
            """, (expiration_date, hashed_device, row['id']))
            if cur.rowcount != 1:
                raise HardwareBindingConflict('Registration was activated concurrently.')
            _bind_hardware(cur, row, hashed_hardware)
        conn.commit()

        return jsonify(
            success=True,
            registration_type=row['registration_type'],
            expiration_date=str(expiration_date) if expiration_date else None
        )
    except Exception as error:
        return _registration_error(conn, error)
    finally:
        conn.close()
