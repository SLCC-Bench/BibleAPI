"""Startup contracts without database connections or background HTTP requests."""
import os
from pathlib import Path
import runpy
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class FakeFlask:
    def __init__(self, *args, **kwargs):
        self.static_folder = kwargs.get("static_folder")
        self.run = Mock()

    def register_blueprint(self, blueprint):
        pass

    def route(self, *args, **kwargs):
        return lambda function: function


class DesktopStartupTests(unittest.TestCase):
    def load_app(self, local=False, frozen=False, schema_only=False):
        init_db = Mock()
        flask = types.ModuleType("flask")
        flask.Flask = FakeFlask
        flask.send_from_directory = Mock()
        cors = types.ModuleType("flask_cors")
        cors.CORS = Mock()
        config = types.ModuleType("config_loader")
        config.load_config_into_environ = Mock(return_value={})
        database = types.ModuleType("db")
        database.init_db = init_db
        modules = {"flask": flask, "flask_cors": cors, "config_loader": config, "db": database}
        for name, blueprint in {
            "users": "users_bp", "bible": "bible_bp", "uploadBible": "upload_bible_bp",
            "updateBible": "update_bible_bp", "webhook": "webhook_bp",
            "languages": "languages_bp", "songs": "songs_bp", "admin": "admin_bp",
        }.items():
            module = types.ModuleType("routes." + name)
            setattr(module, blueprint, object())
            modules["routes." + name] = module
        argv = ["app.py"] + (["--init-db"] if schema_only else [])
        with patch.dict(sys.modules, modules), \
                patch.dict(os.environ, {"BIBLEAPI_LOCAL": "1" if local else "0"}), \
                patch.object(sys, "frozen", frozen, create=True), \
                patch.object(sys, "argv", argv), \
                patch.object(threading, "Thread") as thread:
            namespace = runpy.run_path(str(APP_PATH))
            namespace["main"]()
        return namespace["app"], init_db, thread

    def test_local_startup_does_not_maintain_schema(self):
        app, init_db, thread = self.load_app(local=True)
        init_db.assert_not_called()
        thread.assert_not_called()
        app.run.assert_called_once()

    def test_frozen_startup_does_not_maintain_schema(self):
        app, init_db, thread = self.load_app(frozen=True)
        init_db.assert_not_called()
        thread.assert_not_called()
        app.run.assert_called_once()

    def test_hosted_startup_keeps_schema_initialization(self):
        app, init_db, thread = self.load_app()
        init_db.assert_called_once()
        thread.assert_called_once()
        app.run.assert_called_once()

    def test_explicit_schema_command_does_not_start_server(self):
        for local in (False, True):
            with self.subTest(local=local):
                app, init_db, thread = self.load_app(local=local, schema_only=True)
                init_db.assert_called_once()
                thread.assert_not_called()
                app.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
