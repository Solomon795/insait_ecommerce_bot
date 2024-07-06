# tests/conftest.py
import pytest
from main_app import app as flask_app

@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['DEBUG'] = False
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()
