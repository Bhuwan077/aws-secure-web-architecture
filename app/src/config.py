import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "aws-portfolio-dev-secret-key-change-in-prod")
    
    # Secure storage location outside the public web root
    # Defaults to /var/data/expenses.db on Linux production instance, or local data dir in dev
    DEFAULT_DB_PATH = os.environ.get(
        "DATABASE_PATH",
        str(BASE_DIR / "data" / "expenses.db") if os.name == "nt" else "/var/data/expenses.db"
    )
    
    # Fallback to local app directory if /var/data is not writable (e.g. during local tests)
    DATABASE_PATH = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)
    
    # App environment
    ENVIRONMENT = os.environ.get("APP_ENV", "development")
    APP_VERSION = "1.0.0"
