import os
import tempfile
import pytest
from app.src.app import create_app
from app.src.database import init_db

@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({
        "TESTING": True,
        "DATABASE_PATH": db_path,
        "SECRET_KEY": "test-api-secret-key"
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

def test_api_crud_flow(client):
    """Test full REST API lifecycle: Create -> List -> Read -> Delete."""
    # 1. Create
    payload = {
        "title": "AWS Route 53 Hosted Zone",
        "amount": 0.50,
        "category": "Cloud Infrastructure",
        "date": "2026-10-20",
        "description": "Monthly DNS zone charge"
    }
    res = client.post("/api/expenses", json=payload)
    assert res.status_code == 201
    created = res.get_json()
    expense_id = created["id"]
    assert created["title"] == "AWS Route 53 Hosted Zone"
    assert created["amount"] == 0.50

    # 2. List
    res = client.get("/api/expenses")
    assert res.status_code == 200
    list_data = res.get_json()
    assert list_data["count"] == 1
    assert list_data["data"][0]["id"] == expense_id

    # 3. Read single
    res = client.get(f"/api/expenses/{expense_id}")
    assert res.status_code == 200
    single = res.get_json()
    assert single["id"] == expense_id

    # 4. Check stats
    res = client.get("/api/stats")
    assert res.status_code == 200
    stats = res.get_json()
    assert stats["total_count"] == 1
    assert stats["total_expenses"] == 0.50

    # 5. Delete
    res = client.delete(f"/api/expenses/{expense_id}")
    assert res.status_code == 200

    # 6. Verify Deleted
    res = client.get(f"/api/expenses/{expense_id}")
    assert res.status_code == 404

def test_api_validation_error(client):
    """Verify API returns 422 for invalid payloads."""
    payload = {
        "title": "Invalid Negative Amount",
        "amount": -100,
        "category": "Cloud Infrastructure"
    }
    res = client.post("/api/expenses", json=payload)
    assert res.status_code == 422
    err = res.get_json()
    assert "error" in err
    assert err["error"] == "Validation Error"
