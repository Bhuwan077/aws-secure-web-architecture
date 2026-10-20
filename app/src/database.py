import os
import sqlite3
from pathlib import Path
from typing import Optional
from .config import Config

def get_db_path() -> str:
    """Resolve and ensure the database directory exists securely."""
    db_path = Path(Config.DATABASE_PATH)
    
    # If the configured path cannot be created or accessed, fallback to local app/data directory
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # On POSIX systems, ensure strict folder permissions (read/write/exec for owner only)
        if os.name != "nt":
            os.chmod(db_path.parent, 0o700)
    except (PermissionError, OSError):
        local_dir = Path(__file__).resolve().parent.parent / "data"
        local_dir.mkdir(parents=True, exist_ok=True)
        db_path = local_dir / "expenses.db"
        if os.name != "nt":
            os.chmod(local_dir, 0o700)
            
    return str(db_path)

def get_connection() -> sqlite3.Connection:
    """Return an active SQLite database connection with row factory enabled."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    
    # Enable WAL mode for better concurrency and foreign keys
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # On POSIX systems, ensure strict file permissions on the DB file
    if os.name != "nt" and os.path.exists(db_path):
        try:
            os.chmod(db_path, 0o600)
        except OSError:
            pass
            
    return conn

def init_db():
    """Initialize database schema with idempotent table creation."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    amount REAL NOT NULL CHECK(amount > 0),
                    category TEXT NOT NULL,
                    date TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
            """)
    finally:
        conn.close()

def check_db_health() -> bool:
    """Test database connectivity and write/read capability."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        result = cur.fetchone()
        conn.close()
        return result is not None and result[0] == 1
    except Exception:
        return False
