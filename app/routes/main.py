"""Main routes for the Email Harness QA Agent."""

from flask import Blueprint, request, jsonify, render_template
from app.agents.email_harness import EmailHarnessAgent
from app.config import Config

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Display the web interface."""
    return render_template("index.html")


@main_bp.route("/health")
def health():
    """Health check endpoint."""
    api_key_set = bool(Config.DEEPSEEK_API_KEY and
                       not Config.DEEPSEEK_API_KEY.startswith("sk-your-"))
    return jsonify({
        "status": "healthy",
        "deepseek_api_configured": api_key_set,
    })


@main_bp.route("/review", methods=["POST"])
def review():
    """
    Accept raw email text and return a QA report.

    Request JSON:
        { "email_text": "..." }

    Response JSON:
        { "report": { ... }, "has_previous": true/false }
    """
    data = request.get_json(silent=True)
    if not data or "email_text" not in data:
        return jsonify({"error": "Missing 'email_text' in request body."}), 400

    email_text = data["email_text"]

    # Validate length
    if len(email_text) > Config.MAX_EMAIL_LENGTH:
        return jsonify({
            "error": f"Email too long. Maximum {Config.MAX_EMAIL_LENGTH} characters."
        }), 413

    # Run the Agent
    agent = EmailHarnessAgent()
    report = agent.review(email_text)

    # Convert to dict for JSON serialization
    report_dict = _report_to_dict(report)

    return jsonify({
        "report": report_dict,
    })


def _report_to_dict(report) -> dict:
    """Convert QAReport dataclass to JSON-serializable dict."""
    return {
        "overall_status": report.overall_status,
        "validation_summary": report.validation_summary,
        "issues": [
            {
                "title": i.title,
                "description": i.description,
                "why_it_matters": i.why_it_matters,
                "recommendation": i.recommendation,
                "source": i.source,
            }
            for i in report.issues
        ],
        "ai_review_summary": report.ai_review_summary,
        "final_recommendation": report.final_recommendation,
    }
