import os
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort
from .config import Config
from .database import init_db, check_db_health, get_db_path
from .models import ExpenseModel, ValidationError, ALLOWED_CATEGORIES

START_TIME = time.time()

def create_app(test_config=None):
    """Application factory for the Expense Tracker web service."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Initialize the database schema
    with app.app_context():
        init_db()

    # --- Security Headers Middleware ---
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy: restrict scripts/styles to self and reputable CDN for charts/icons
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # --- Prevent Direct Access to DB files ---
    @app.before_request
    def block_sensitive_files():
        path = request.path.lower()
        if path.endswith(".db") or path.endswith(".sqlite") or ".." in path or "/.git" in path:
            abort(403)

    # --- Health Check Endpoint (AWS ALB / CloudWatch target) ---
    @app.route("/healthz", methods=["GET"])
    def health_check():
        """
        Unauthenticated health check endpoint.
        Returns HTTP 200 when instance and database are healthy.
        Returns HTTP 503 if database connectivity fails.
        """
        db_healthy = check_db_health()
        uptime_seconds = round(time.time() - START_TIME, 2)
        
        status_code = 200 if db_healthy else 503
        payload = {
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": Config.APP_VERSION,
            "environment": Config.ENVIRONMENT,
            "uptime_seconds": uptime_seconds,
            "checks": {
                "database": "connected" if db_healthy else "disconnected",
                "storage": "writable"
            }
        }
        return jsonify(payload), status_code

    # --- HTML UI Routes ---
    @app.route("/", methods=["GET"])
    def index():
        category_filter = request.args.get("category", "").strip()
        search_query = request.args.get("q", "").strip()
        
        expenses = ExpenseModel.get_all(
            category=category_filter or None,
            search=search_query or None
        )
        stats = ExpenseModel.get_summary_stats()
        
        return render_template(
            "index.html",
            expenses=expenses,
            stats=stats,
            categories=ALLOWED_CATEGORIES,
            selected_category=category_filter,
            search_query=search_query,
            today=datetime.utcnow().strftime("%Y-%m-%d")
        )

    @app.route("/expenses/new", methods=["POST"])
    def add_expense():
        try:
            title = request.form.get("title", "")
            amount = request.form.get("amount", "")
            category = request.form.get("category", "")
            date_str = request.form.get("date", "")
            description = request.form.get("description", "")

            ExpenseModel.create(title, amount, category, date_str, description)
            flash("Expense record added successfully.", "success")
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
        except Exception as e:
            flash("An unexpected error occurred while saving the expense.", "danger")

        return redirect(url_for("index"))

    @app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
    def edit_expense(expense_id):
        expense = ExpenseModel.get_by_id(expense_id)
        if not expense:
            flash("Expense record not found.", "warning")
            return redirect(url_for("index"))

        if request.method == "POST":
            try:
                title = request.form.get("title", "")
                amount = request.form.get("amount", "")
                category = request.form.get("category", "")
                date_str = request.form.get("date", "")
                description = request.form.get("description", "")

                ExpenseModel.update(expense_id, title, amount, category, date_str, description)
                flash("Expense record updated successfully.", "success")
                return redirect(url_for("index"))
            except ValidationError as e:
                flash(f"Validation Error: {str(e)}", "danger")
            except Exception:
                flash("An unexpected error occurred while updating the expense.", "danger")

        return render_template("edit.html", expense=expense, categories=ALLOWED_CATEGORIES)

    @app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
    def delete_expense(expense_id):
        deleted = ExpenseModel.delete(expense_id)
        if deleted:
            flash("Expense record deleted successfully.", "info")
        else:
            flash("Expense record could not be found.", "warning")
        return redirect(url_for("index"))

    # --- REST API Endpoints ---
    @app.route("/api/expenses", methods=["GET"])
    def api_get_expenses():
        category = request.args.get("category")
        search = request.args.get("q")
        expenses = ExpenseModel.get_all(category=category, search=search)
        return jsonify({"count": len(expenses), "data": expenses}), 200

    @app.route("/api/expenses/<int:expense_id>", methods=["GET"])
    def api_get_expense(expense_id):
        expense = ExpenseModel.get_by_id(expense_id)
        if not expense:
            return jsonify({"error": "Not Found", "message": f"Expense {expense_id} does not exist"}), 404
        return jsonify(expense), 200

    @app.route("/api/expenses", methods=["POST"])
    def api_create_expense():
        if not request.is_json:
            return jsonify({"error": "Bad Request", "message": "JSON body required"}), 400
        data = request.get_json()
        try:
            created = ExpenseModel.create(
                title=data.get("title"),
                amount=data.get("amount"),
                category=data.get("category"),
                date_str=data.get("date"),
                description=data.get("description")
            )
            return jsonify(created), 201
        except ValidationError as e:
            return jsonify({"error": "Validation Error", "message": str(e)}), 422
        except Exception:
            return jsonify({"error": "Internal Error", "message": "Failed to record expense"}), 500

    @app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
    def api_delete_expense(expense_id):
        deleted = ExpenseModel.delete(expense_id)
        if not deleted:
            return jsonify({"error": "Not Found", "message": f"Expense {expense_id} not found"}), 404
        return jsonify({"message": f"Expense {expense_id} successfully deleted"}), 200

    @app.route("/api/stats", methods=["GET"])
    def api_get_stats():
        stats = ExpenseModel.get_summary_stats()
        return jsonify(stats), 200

    # --- Error Handlers ---
    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Forbidden", "message": "Access denied"}), 403
        return render_template("base.html", error_title="403 Forbidden", error_message="Access denied."), 403

    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not Found", "message": "Resource not found"}), 404
        return render_template("base.html", error_title="404 Not Found", error_message="The requested page does not exist."), 404

    @app.errorhandler(500)
    def internal_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500
        return render_template("base.html", error_title="500 Server Error", error_message="An internal server error occurred."), 500

    return app

# WSGI entrypoint for Gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
