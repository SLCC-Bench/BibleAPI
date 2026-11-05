"""Authentication boundaries using test credentials and no real database."""
import hashlib
import json
import os
import unittest
from unittest.mock import patch

from flask import Flask, jsonify
from werkzeug.security import generate_password_hash
import local_security


class LocalSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.credentials = json.dumps({
            'username_hash': hashlib.sha256(b'test-admin').hexdigest(),
            'password_hash': generate_password_hash('test-password', method='pbkdf2:sha256:1000'),
        })

    def setUp(self):
        app = Flask(__name__)
        app.testing = True
        with patch.dict(os.environ, {'BIBLEAPI_APP_TOKEN': 'test-runtime-token'}), \
                patch.object(local_security.Path, 'read_text', return_value=self.credentials):
            local_security.install_local_security(app)
        for index, path in enumerate(['/api/translations', '/api/registration-codes/check',
                                      '/api/registration-codes/events', '/api/users',
                                      '/api/registration-codes/1/replacement']):
            app.add_url_rule(path, f'test_{index}', lambda: jsonify(ok=True), methods=['GET', 'POST'])
        self.client = app.test_client()

    def login(self, password='test-password'):
        csrf = self.client.get('/auth/session').json['csrf']
        return self.client.post('/auth/login', json={'username': 'test-admin', 'password': password},
                                headers={'X-CSRF-Token': csrf})

    def test_anonymous_clients_cannot_read_api_or_admin_files(self):
        for path in ['/api/translations', '/api/users', '/api/registration-codes/events', '/readyz']:
            self.assertEqual(self.client.get(path).status_code, 401)
        for path in ['/static/admin.html', '/static/js/admin.js', '/routes']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith('/login'))

    def test_valid_login_enables_admin_and_invalid_login_does_not(self):
        self.assertEqual(self.login('wrong-password').status_code, 401)
        self.assertEqual(self.client.get('/api/users').status_code, 401)
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get('/api/users').status_code, 200)

    def test_admin_writes_and_logout_require_csrf(self):
        self.login()
        path = '/api/registration-codes/1/replacement'
        self.assertEqual(self.client.post(path).status_code, 403)
        csrf = self.client.get('/auth/session').json['csrf']
        self.assertEqual(self.client.post(path, headers={'X-CSRF-Token': csrf}).status_code, 200)
        self.assertEqual(self.client.post('/auth/logout').status_code, 403)
        self.assertEqual(self.client.post('/auth/logout', headers={'X-CSRF-Token': csrf}).status_code, 200)
        self.assertEqual(self.client.get('/api/users').status_code, 401)

    def test_runtime_token_allows_app_operations_but_not_admin_operations(self):
        headers = {'X-Praisehub-Token': 'test-runtime-token', 'Origin': 'null'}
        self.assertEqual(self.client.get('/api/translations', headers=headers).status_code, 200)
        self.assertEqual(self.client.post('/api/registration-codes/check', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/api/registration-codes/events', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/api/users', headers=headers).status_code, 401)
        self.assertEqual(self.client.post('/api/registration-codes/1/replacement', headers=headers).status_code, 401)
        self.assertEqual(self.client.get('/api/translations', headers={'X-Praisehub-Token': 'wrong'}).status_code, 401)

    def test_login_csrf_rate_limit_and_network_origin_boundaries(self):
        self.assertEqual(self.client.post('/auth/login', json={'username': 'test-admin', 'password': 'test-password'}).status_code, 403)
        for _ in range(5):
            self.assertEqual(self.login('wrong-password').status_code, 401)
        self.assertEqual(self.login('wrong-password').status_code, 429)
        for headers in [{'Host': 'attacker.example'}, {'Origin': 'https://attacker.example'}]:
            self.assertEqual(self.client.get('/auth/session', headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/auth/session', environ_overrides={'REMOTE_ADDR': '192.168.1.9'}).status_code, 403)

    def test_login_rotates_csrf_and_session_cookie_is_http_only(self):
        before = self.client.get('/auth/session').json['csrf']
        response = self.login()
        self.assertIn('HttpOnly', response.headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', response.headers['Set-Cookie'])
        self.assertNotEqual(self.client.get('/auth/session').json['csrf'], before)
