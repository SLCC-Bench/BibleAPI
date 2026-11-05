"""Same-device restoration without changing real registrations."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from copy import deepcopy
from datetime import date, timedelta
from unittest.mock import patch

import bcrypt
from flask import Flask


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params):
        normalized = ' '.join(sql.split())
        self.connection.statements.append((normalized, params))
        row = self.connection.row
        if normalized.startswith('SELECT'):
            if 'hardware_device_id' in normalized and not self.connection.hardware_schema:
                raise RuntimeError(1054, 'Unknown column')
            if ('WHERE id =' in normalized and 'FOR UPDATE' in normalized
                    and 'registration_type' in normalized and self.connection.before_locked_reload):
                callback = self.connection.before_locked_reload
                self.connection.before_locked_reload = None
                callback(self.connection)
            field = next((field for field in ['hardware_device_id', 'device_id', 'id'] if f'WHERE {field} =' in normalized), 'registration_code')
            row = next((row for row in self.connection.rows if row[field] == params[0]), None)
            columns = normalized.split(' FROM ')[0].removeprefix('SELECT ').split(', ')
            self.result = {key: row[key] for key in columns} if row else None
        elif normalized.startswith('UPDATE RegistrationCodes SET hardware_device_id'):
            row = next(row for row in self.connection.rows if row['id'] == params[1])
            if self.connection.binding_conflict:
                row['hardware_device_id'] = 'concurrent-binding'
            self.rowcount = int(row['hardware_device_id'] is None)
            if self.rowcount:
                row['hardware_device_id'] = params[0]
        elif normalized.startswith('UPDATE RegistrationCodes SET device_id = %s'):
            row['device_id'] = params[0]
        elif normalized.startswith('UPDATE'):
            if 'SET is_used = 1' in normalized:
                row = next(row for row in self.connection.rows if row['id'] == params[2])
                self.rowcount = int(not row['is_used'])
                if self.rowcount:
                    row.update(is_used=1, expiration_date=params[0], device_id=params[1])
            elif 'SET device_id = NULL' in normalized:
                row = next(row for row in self.connection.rows if row['id'] == params[0])
                row['device_id'] = None
                if 'hardware_device_id = NULL' in normalized:
                    row['hardware_device_id'] = None
            else:
                raise AssertionError('Unexpected registration update')

    def fetchone(self):
        return self.result


class Connection:
    def __init__(self, row):
        self.row = row
        self.rows = [row]
        self.original = deepcopy(row)
        self.commits = 0
        self.statements = []
        self.hardware_schema = True
        self.binding_conflict = False
        self.before_locked_reload = None

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.row.clear()
        self.row.update(deepcopy(self.original))

    def close(self):
        pass


class RegistrationReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database = types.ModuleType('db')
        database.get_db_connection = lambda: None
        spec = importlib.util.spec_from_file_location('registration_reuse_admin', Path(__file__).resolve().parents[1] / 'routes' / 'admin.py')
        cls.admin = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'db': database}):
            spec.loader.exec_module(cls.admin)
        app = Flask(__name__)
        app.register_blueprint(cls.admin.admin_bp)
        cls.client = app.test_client()
        cls.code = 'same-device-test-key'
        cls.hashed_code = bcrypt.hashpw(cls.code.encode(), bcrypt.gensalt(rounds=4)).decode()

    def redeem(self, *, device='original-device', stored_device=None, stored_code=None,
               submitted_code=None, reg_type='permanent', expires=None):
        row = {
            'id': 1, 'registration_type': reg_type, 'expiration_date': expires,
            'registration_code': self.hashed_code if stored_code is None else stored_code,
            'is_used': 1, 'trial_days': 7,
            'device_id': self.admin.hash_device_id('original-device') if stored_device is None else stored_device,
            'hardware_device_id': None,
        }
        connection = Connection(row)
        with patch.object(self.admin, 'get_db_connection', return_value=connection):
            response = self.client.post('/api/registration-codes/redeem', json={
                'registration_code': submitted_code or self.code, 'device_id': device,
            })
        return response, connection

    def test_same_device_can_restore_permanent_key(self):
        response, connection = self.redeem()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
        self.assertIsNone(response.json['expiration_date'])
        self.assertEqual(connection.commits, 1)

    def test_trial_restoration_preserves_original_expiry(self):
        expiry = date.today() + timedelta(days=2)
        response, connection = self.redeem(reg_type='trial', expires=expiry)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['expiration_date'], str(expiry))
        self.assertEqual(connection.row['expiration_date'], expiry)

    def test_expired_trial_is_not_reactivated(self):
        response, connection = self.redeem(reg_type='trial', expires=date.today() - timedelta(days=1))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(connection.commits, 0)

    def test_wrong_key_does_not_restore_active_device(self):
        response, _ = self.redeem(submitted_code='wrong-key')
        self.assertEqual(response.status_code, 409)

    def test_same_key_does_not_activate_another_device(self):
        response, connection = self.redeem(device='different-device')
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(connection.commits, 0)

    def test_legacy_plaintext_key_and_device_are_restored_and_migrated(self):
        response, connection = self.redeem(stored_device='original-device', stored_code=self.code)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(connection.row['device_id'], self.admin.hash_device_id('original-device'))
        self.assertEqual(connection.commits, 1)


if __name__ == '__main__':
    unittest.main()
