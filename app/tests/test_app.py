import os
import tempfile
import pytest
from app.src.app import create_app
from app.src.database import init_db

@pytest.fixture
def client():
    """Create and configure a testing client using an isolated temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({
        "TESTING": True,
        "DATABASE_PATH": db_path,
        "SECRET_KEY": "test-secret-key"
    })

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

def test_health_check(client):
    """Verify /healthz returns 200 and valid JSON health payload."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["checks"]["database"] == "connected"
    assert "uptime_seconds" in data
    assert "version" in data

def test_index_page(client):
    """Verify home page loads and displays brand titles."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"CloudSpend Tracker" in response.data
    assert b"Total Spend" in response.data

def test_add_expense_form(client):
    """Verify adding an expense redirects and creates a database row."""
    response = client.post("/expenses/new", data={
        "title": "AWS EC2 t3.micro",
        "amount": "10.50",
        "category": "Cloud Infrastructure",
        "date": "2026-10-20",
        "description": "Dev instance hosting expense tracker"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"AWS EC2 t3.micro" in response.data
    assert b"10.50" in response.data

def test_validation_negative_amount(client):
    """Verify negative amounts are rejected."""
    response = client.post("/expenses/new", data={
        "title": "Invalid Negative",
        "amount": "-50.00",
        "category": "Cloud Infrastructure",
        "date": "2026-10-20"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Validation Error" in response.data

def test_validation_empty_title(client):
    """Verify empty titles are rejected."""
    response = client.post("/expenses/new", data={
        "title": "   ",
        "amount": "15.00",
        "category": "Cloud Infrastructure",
        "date": "2026-10-20"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Validation Error" in response.data

def test_block_database_download(client):
    """Verify direct HTTP requests to .db files are blocked with 403 Forbidden."""
    response = client.get("/data/expenses.db")
    assert response.status_code == 403
    
    response2 = client.get("/static/../data/expenses.sqlite")
    assert response2.status_code == 403

def test_security_headers(client):
    """Verify security headers are applied to HTTP responses."""
    response = client.get("/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in response.headers
