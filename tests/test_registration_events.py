"""Local registration change notifications without a database or running server."""
import unittest
from unittest.mock import patch

import test_registration_reuse as fixtures


class RegistrationEventTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.RegistrationReuseTests.setUpClass.__func__)

    def test_stream_reconciles_on_connect_and_notifies_after_change_without_db(self):
        with patch.object(self.admin, 'get_db_connection') as database:
            response = self.client.get('/api/registration-codes/events', buffered=False)
            try:
                self.assertEqual(response.mimetype, 'text/event-stream')
                self.assertIn(b'event: registration-changed', next(response.response))
                self.admin._notify_registration_changed()
                self.assertEqual(next(response.response), b'event: registration-changed\ndata: {}\n\n')
                database.assert_not_called()
            finally:
                response.close()

    def test_idle_heartbeat_does_not_query_db_or_emit_a_change(self):
        with patch.object(self.admin, 'get_db_connection') as database:
            response = self.client.get('/api/registration-codes/events', buffered=False)
            try:
                next(response.response)
                with patch.object(self.admin._registration_changes, 'wait_for', return_value=False):
                    self.assertEqual(next(response.response), b': keep-alive\n\n')
                database.assert_not_called()
            finally:
                response.close()

    def test_stream_is_not_exposed_to_remote_clients(self):
        response = self.client.get('/api/registration-codes/events', environ_overrides={'REMOTE_ADDR': '192.168.1.20'})
        self.assertEqual(response.status_code, 403)

    def test_permission_notification_is_published_only_after_commit(self):
        connection = fixtures.Connection({
            'id': 1, 'is_used': 1, 'device_id': 'hashed-device', 'hardware_device_id': None,
        })
        with patch.object(self.admin, 'get_db_connection', return_value=connection), \
                patch.object(self.admin, '_notify_registration_changed',
                             side_effect=lambda: self.assertEqual(connection.commits, 1)) as notify:
            response = self.client.post('/api/registration-codes/1/replacement', json={'allowed': True})
            self.assertEqual(response.status_code, 200)
            notify.assert_called_once()

    def test_rejected_permission_change_publishes_nothing(self):
        connection = fixtures.Connection({
            'id': 1, 'is_used': 0, 'device_id': None, 'hardware_device_id': None,
        })
        with patch.object(self.admin, 'get_db_connection', return_value=connection), \
                patch.object(self.admin, '_notify_registration_changed') as notify:
            response = self.client.post('/api/registration-codes/1/replacement', json={'allowed': True})
            self.assertEqual(response.status_code, 400)
            notify.assert_not_called()
