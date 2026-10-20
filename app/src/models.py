import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from .database import get_connection

ALLOWED_CATEGORIES = [
    "Cloud Infrastructure",
    "Software & Tools",
    "Office & Hardware",
    "Travel & Transport",
    "Meals & Entertainment",
    "Utilities",
    "Training & Certifications",
    "Miscellaneous"
]

class ValidationError(Exception):
    """Raised when user input violates validation rules."""
    pass

class ExpenseModel:
    @staticmethod
    def validate(title: str, amount: Any, category: str, date_str: str, description: Optional[str] = None) -> Tuple[str, float, str, str, str]:
        """Validate expense input fields securely."""
        if not title or not isinstance(title, str) or not title.strip():
            raise ValidationError("Title is required and must not be empty.")
        title = title.strip()
        if len(title) > 100:
            raise ValidationError("Title must not exceed 100 characters.")

        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValidationError("Amount must be greater than zero.")
            if amount_val > 1_000_000:
                raise ValidationError("Amount exceeds allowable threshold ($1,000,000).")
            # Round to 2 decimal places
            amount_val = round(amount_val, 2)
        except (ValueError, TypeError):
            raise ValidationError("Amount must be a valid positive number.")

        if category not in ALLOWED_CATEGORIES:
            raise ValidationError(f"Invalid category '{category}'. Must be one of: {', '.join(ALLOWED_CATEGORIES)}")

        # Validate date format (YYYY-MM-DD)
        if not date_str:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
        else:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Date must be in YYYY-MM-DD format.")

        description = (description or "").strip()
        if len(description) > 500:
            raise ValidationError("Description must not exceed 500 characters.")

        return title, amount_val, category, date_str, description

    @classmethod
    def get_all(cls, category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all expenses with optional filtering."""
        conn = get_connection()
        query = "SELECT * FROM expenses WHERE 1=1"
        params = []

        if category and category in ALLOWED_CATEGORIES:
            query += " AND category = ?"
            params.append(category)

        if search:
            query += " AND (title LIKE ? OR description LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        query += " ORDER BY date DESC, id DESC"

        try:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, expense_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single expense by ID."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @classmethod
    def create(cls, title: str, amount: Any, category: str, date_str: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new expense entry after validation."""
        valid_title, valid_amount, valid_category, valid_date, valid_desc = cls.validate(
            title, amount, category, date_str, description
        )
        conn = get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO expenses (title, amount, category, date, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (valid_title, valid_amount, valid_category, valid_date, valid_desc))
                new_id = cur.lastrowid
                
            return cls.get_by_id(new_id)
        finally:
            conn.close()

    @classmethod
    def update(cls, expense_id: int, title: str, amount: Any, category: str, date_str: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update an existing expense entry."""
        valid_title, valid_amount, valid_category, valid_date, valid_desc = cls.validate(
            title, amount, category, date_str, description
        )
        conn = get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE expenses
                    SET title = ?, amount = ?, category = ?, date = ?, description = ?
                    WHERE id = ?
                """, (valid_title, valid_amount, valid_category, valid_date, valid_desc, expense_id))
                if cur.rowcount == 0:
                    return None
            return cls.get_by_id(expense_id)
        finally:
            conn.close()

    @classmethod
    def delete(cls, expense_id: int) -> bool:
        """Delete an expense by ID."""
        conn = get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
                return cur.rowcount > 0
        finally:
            conn.close()

    @classmethod
    def get_summary_stats(cls) -> Dict[str, Any]:
        """Compute aggregated statistics for the dashboard."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            # Total and count
            cur.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0.0), COALESCE(AVG(amount), 0.0) FROM expenses")
            count, total, avg_val = cur.fetchone()

            # By category
            cur.execute("""
                SELECT category, COUNT(*) as count, SUM(amount) as total
                FROM expenses
                GROUP BY category
                ORDER BY total DESC
            """)
            by_category = [dict(row) for row in cur.fetchall()]

            # Monthly trends
            cur.execute("""
                SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
                FROM expenses
                GROUP BY month
                ORDER BY month DESC
                LIMIT 6
            """)
            monthly_trends = [dict(row) for row in cur.fetchall()]

            return {
                "total_expenses": round(total, 2),
                "total_count": count,
                "average_expense": round(avg_val, 2),
                "by_category": by_category,
                "monthly_trends": monthly_trends
            }
        finally:
            conn.close()
