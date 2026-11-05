"""Hardware migration and reformat restoration without a real database."""
from datetime import date, timedelta
import unittest
from unittest.mock import patch

import test_registration_reuse as fixtures


class HardwareBindingTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.RegistrationReuseTests.setUpClass.__func__)
    hardware = 'a' * 64
    other_hardware = 'b' * 64

    def connection(self, *, bound=True, used=True, trial=False, expired=False):
        expiry = date.today() + timedelta(days=-1 if expired else 2) if trial else None
        return fixtures.Connection({
            'id': 1, 'registration_type': 'trial' if trial else 'permanent',
            'expiration_date': expiry, 'registration_code': self.hashed_code if used else self.code,
            'is_used': int(used), 'trial_days': 7,
            'device_id': self.admin.hash_device_id('original-device') if used else None,
            'hardware_device_id': self.admin.hash_hardware_id(self.hardware) if bound else None,
        })

    def request(self, connection, *, redeem=False, device='original-device', hardware=None, code=None):
        payload = {'device_id': device, 'hardware_id': hardware if hardware is not None else self.hardware}
        if redeem:
            payload['registration_code'] = self.code if code is None else code
        with patch.object(self.admin, 'get_db_connection', return_value=connection):
            return self.client.post('/api/registration-codes/' + ('redeem' if redeem else 'check'), json=payload)

    def test_existing_active_os_binding_is_linked_without_replacing_it(self):
        connection = self.connection(bound=False)
        original = connection.row['device_id']
        response = self.request(connection)
        self.assertTrue(response.json['registered'])
        self.assertEqual(connection.row['device_id'], original)
        self.assertEqual(connection.row['hardware_device_id'], self.admin.hash_hardware_id(self.hardware))
        self.assertNotEqual(connection.row['hardware_device_id'], self.hardware)

    def test_same_hardware_restores_after_os_identity_changes(self):
        connection = self.connection(trial=True)
        original = dict(connection.row)
        response = self.request(connection, device='reformatted-os')
        self.assertTrue(response.json['registered'])
        self.assertEqual(response.json['expiration_date'], str(original['expiration_date']))
        self.assertEqual(connection.row, original)

    def test_hardware_only_request_restores_existing_registration(self):
        response = self.request(self.connection(), device=None)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['registered'])

    def test_original_key_can_be_reentered_after_reformat_without_renewing_trial(self):
        connection = self.connection(trial=True)
        expiry = connection.row['expiration_date']
        response = self.request(connection, redeem=True, device='reformatted-os')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(connection.row['expiration_date'], expiry)
        self.assertEqual(response.json['expiration_date'], str(expiry))

    def test_wrong_key_on_known_hardware_is_rejected(self):
        response = self.request(self.connection(), redeem=True, device='reformatted-os', code='wrong-key')
        self.assertEqual(response.status_code, 409)

    def test_legacy_os_identity_cannot_replace_a_different_hardware_binding(self):
        connection = self.connection()
        original = connection.row['hardware_device_id']
        response = self.request(connection, hardware=self.other_hardware)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(connection.row['hardware_device_id'], original)

    def test_used_key_cannot_be_transferred_to_unrecognized_hardware(self):
        connection = self.connection()
        response = self.request(connection, redeem=True, device='different-device', hardware=self.other_hardware)
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(connection.commits, 0)

    def test_unused_key_can_bind_hardware_without_raw_os_identity(self):
        connection = self.connection(bound=False, used=False)
        response = self.request(connection, redeem=True, device=None)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(connection.row['device_id'])
        self.assertEqual(connection.row['hardware_device_id'], self.admin.hash_hardware_id(self.hardware))

    def test_newly_activated_key_remains_readable(self):
        connection = self.connection(bound=False, used=False)
        response = self.request(connection, redeem=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(connection.row['registration_code'], self.code)
        self.assertTrue(connection.row['is_used'])
        self.assertNotEqual(connection.row['hardware_device_id'], self.hardware)

    def test_plaintext_key_reuse_after_reformat_preserves_expiry(self):
        connection = self.connection(bound=False, used=False, trial=True)
        self.assertEqual(self.request(connection, redeem=True).status_code, 200)
        expiry = connection.row['expiration_date']
        response = self.request(connection, redeem=True, device='reformatted-os')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(connection.row['registration_code'], self.code)
        self.assertEqual(response.json['expiration_date'], str(expiry))
        self.assertEqual(connection.row['expiration_date'], expiry)

    def test_readable_used_key_still_cannot_activate_another_device(self):
        connection = self.connection(bound=False, used=False)
        self.assertEqual(self.request(connection, redeem=True).status_code, 200)
        response = self.request(connection, redeem=True, device='another-device', hardware=self.other_hardware)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(connection.row['registration_code'], self.code)

    def test_old_client_still_uses_legacy_identity_without_new_column(self):
        connection = self.connection()
        connection.hardware_schema = False
        response = self.request(connection, hardware='')
        self.assertTrue(response.json['registered'])

    def test_missing_migration_is_reported_instead_of_silent_legacy_activation(self):
        connection = self.connection(bound=False)
        connection.hardware_schema = False
        response = self.request(connection)
        self.assertEqual(response.status_code, 503)
        self.assertIn('migration', response.json['error'])

    def test_invalid_hardware_identity_is_rejected_before_database_access(self):
        connection = self.connection()
        response = self.request(connection, hardware='raw-physical-uuid')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(connection.statements, [])

    def test_concurrent_binding_conflict_rolls_back(self):
        connection = self.connection(bound=False)
        connection.binding_conflict = True
        response = self.request(connection)
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(connection.row['hardware_device_id'])

    def test_expired_trial_is_not_linked_to_new_hardware(self):
        connection = self.connection(bound=False, trial=True, expired=True)
        response = self.request(connection)
        self.assertTrue(response.json['is_expired'])
        self.assertIsNone(connection.row['hardware_device_id'])

    def test_expiry_changed_before_locked_reload_is_not_ignored(self):
        connection = self.connection(bound=False, trial=True)
        connection.before_locked_reload = lambda conn: conn.row.update(
            expiration_date=date.today() - timedelta(days=1))
        response = self.request(connection)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['is_expired'])
        self.assertIsNone(connection.row['hardware_device_id'])

    def test_deleted_registration_before_locked_reload_is_not_restored(self):
        connection = self.connection(bound=False)
        connection.before_locked_reload = lambda conn: conn.rows.clear()
        response = self.request(connection)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json['registered'])
        self.assertIsNone(connection.row['hardware_device_id'])

    def test_expired_key_on_known_hardware_cannot_be_renewed(self):
        connection = self.connection(trial=True, expired=True)
        response = self.request(connection, redeem=True, device='reformatted-os')
        self.assertEqual(response.status_code, 403)

    def test_legacy_client_new_key_renewal_preserves_existing_hardware_link(self):
        connection = self.connection(trial=True, expired=True)
        hardware = connection.row['hardware_device_id']
        new_row = dict(connection.row, id=2, registration_code='fresh-key', is_used=0,
                       device_id=None, hardware_device_id=None, expiration_date=None)
        connection.rows.append(new_row)
        response = self.request(connection, redeem=True, hardware='', code='fresh-key')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(connection.row['hardware_device_id'])
        self.assertEqual(new_row['hardware_device_id'], hardware)


if __name__ == '__main__':
    unittest.main()
