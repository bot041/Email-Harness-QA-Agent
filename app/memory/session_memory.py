"""Session-based memory for comparing consecutive email reviews."""

import hashlib
from flask import session


class SessionMemory:
    """
    Store the most recent review in the Flask session.
    Enables comparison between the previous and current review.
    """

    PREVIOUS_REVIEW_KEY = "previous_review"
    PREVIOUS_EMAIL_HASH_KEY = "previous_email_hash"

    @staticmethod
    def store_review(report_dict: dict, email_text: str):
        """Store the current review as the 'previous' for next comparison."""
        email_hash = hashlib.sha256(email_text.encode()).hexdigest()
        session[SessionMemory.PREVIOUS_REVIEW_KEY] = report_dict
        session[SessionMemory.PREVIOUS_EMAIL_HASH_KEY] = email_hash

    @staticmethod
    def get_previous_review() -> dict | None:
        """Retrieve the previously stored review, or None."""
        return session.get(SessionMemory.PREVIOUS_REVIEW_KEY)

    @staticmethod
    def has_previous_review() -> bool:
        """Check if a previous review exists in session."""
        return SessionMemory.PREVIOUS_REVIEW_KEY in session

    @staticmethod
    def compare(current_report: dict, previous_report: dict) -> dict:
        """
        Compare current and previous reviews.

        Returns a comparison report identifying:
        - Fixed issues (in previous but not current)
        - Remaining issues (in both)
        - New issues (in current but not previous)
        """
        # Create issue fingerprints for comparison
        def fingerprint(issue: dict) -> str:
            title = issue.get("title", "")
            desc = issue.get("description", "")
            return hashlib.md5(f"{title}|{desc}".encode()).hexdigest()

        prev_issues = previous_report.get("issues", [])
        curr_issues = current_report.get("issues", [])

        prev_fingerprints = {fingerprint(i): i for i in prev_issues}
        curr_fingerprints = {fingerprint(i): i for i in curr_issues}

        fixed = []
        for fp, issue in prev_fingerprints.items():
            if fp not in curr_fingerprints:
                fixed.append(issue)

        remaining = []
        for fp, issue in curr_fingerprints.items():
            if fp in prev_fingerprints:
                remaining.append(issue)

        new_issues = []
        for fp, issue in curr_fingerprints.items():
            if fp not in prev_fingerprints:
                new_issues.append(issue)

        # Determine comparison summary
        prev_count = len(prev_issues)
        curr_count = len(curr_issues)

        if curr_count == 0:
            comparison = "All previous issues have been resolved."
        elif curr_count < prev_count:
            comparison = (
                f"Improved! {len(fixed)} issue(s) fixed. "
                f"{len(remaining)} issue(s) remain, {len(new_issues)} new issue(s) found."
            )
        elif curr_count == prev_count and not new_issues:
            comparison = "No changes detected — the same issues remain."
        elif curr_count > prev_count:
            comparison = (
                f"More issues found. {len(fixed)} issue(s) fixed, but "
                f"{len(new_issues)} new issue(s) introduced. "
                f"{len(remaining)} issue(s) still remain."
            )
        else:
            comparison = (
                f"Different issues found. {len(fixed)} fixed, "
                f"{len(new_issues)} new, {len(remaining)} remain."
            )

        return {
            "fixed_issues": fixed,
            "remaining_issues": remaining,
            "new_issues": new_issues,
            "comparison": comparison,
            "previous_issue_count": prev_count,
            "current_issue_count": curr_count,
        }

    @staticmethod
    def clear():
        """Clear stored review from session."""
        session.pop(SessionMemory.PREVIOUS_REVIEW_KEY, None)
        session.pop(SessionMemory.PREVIOUS_EMAIL_HASH_KEY, None)
