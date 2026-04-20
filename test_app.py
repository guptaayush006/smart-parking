import pytest
from app import app, init_db, get_db
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

def test_index_page(client):
    """Test the index page loads securely"""
    rv = client.get('/')
    assert rv.status_code == 200

def test_login_page(client):
    """Test the login page loads"""
    rv = client.get('/login')
    assert rv.status_code == 200

def test_user_dashboard_redirect_without_login(client):
    """Test that dashboard redirects to login if not logged in"""
    rv = client.get('/user_dashboard')
    assert rv.status_code == 302
    assert '/login' in rv.headers['Location']

def test_api_slots(client):
    """Test getting slots initially responds ok"""
    rv = client.get('/api/slots')
    assert rv.status_code == 200
    assert len(rv.json) >= 50  # there are 50 initialized slots
