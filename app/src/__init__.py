"""
Expense Tracker Application Package.
Production-ready, lightweight Flask backend designed for secure AWS EC2 deployment.
"""
from .app import create_app

__all__ = ["create_app"]
