"""Email Harness Agent — the single orchestrator.

The Agent is the central coordinator that:
1. Receives the goal ("Review this email")
2. Parses the email
3. Invokes all validators (Rule Engine + DeepSeek)
4. Aggregates results
5. Produces a unified QA Report
"""

import re

from app.utils.email_parser import parse_email
from app.validators.rule_engine import run_rule_engine
from app.services.deepseek_service import review_with_deepseek
from app.validators.models import Issue, QAReport

# Patterns that indicate a false positive about Harness template expressions
_HARNESS_PATTERN = re.compile(r"<\+\w+")
_HARNESS_KEYWORDS = re.compile(
    r"placeholder|unresolved|template expression|harness|not resolved",
    re.IGNORECASE,
)


class EmailHarnessAgent:
    """
    Single AI Agent that orchestrates email QA review.

    Responsibilities:
    - Parse raw email into structured fields
    - Run deterministic rule-based validators
    - Run DeepSeek semantic review
    - Aggregate all findings into a professional QA report
    """

    def __init__(self):
        self.goal = "Review this email."

    def review(self, raw_email_text: str) -> QAReport:
        """
        Execute the full review pipeline and return a QA report.

        Args:
            raw_email_text: The complete email as raw text from the user.

        Returns:
            QAReport with overall status, issues, and recommendations.
        """
        # Step 1: Parse the email
        parsed_email = parse_email(raw_email_text)

        # Step 2: Run Rule Engine (deterministic validators)
        rule_results = run_rule_engine(parsed_email)

        # Step 3: Run DeepSeek semantic review
        deepseek_result = review_with_deepseek(parsed_email)

        # Step 4: Aggregate all issues
        all_issues = []

        # Collect rule engine issues
        for result in rule_results:
            for issue in result.issues:
                issue.source = "rule_engine"
                all_issues.append(issue)

        # Collect DeepSeek issues
        raw_deepseek_issues = deepseek_result.get("issues", [])
        for issue_dict in raw_deepseek_issues:
            issue = Issue(
                title=issue_dict.get("title", "Untitled Issue"),
                description=issue_dict.get("description", ""),
                why_it_matters=issue_dict.get("why_it_matters", ""),
                recommendation=issue_dict.get("recommendation", ""),
                source="deepseek",
            )
            all_issues.append(issue)

        # Step 5: Filter out Harness template expression false positives
        all_issues, filtered_count = self._filter_harness_false_positives(all_issues)

        # Step 5b: If ALL DeepSeek issues were false positives, treat the
        # semantic review as clean so the report doesn't show a contradictory
        # "0 issues but Not Ready to Send" status
        deepseek_assessment = deepseek_result.get("overall_assessment", "Needs Review")
        ai_summary = deepseek_result.get("summary", "")

        if filtered_count > 0 and not any(
            i.source == "deepseek" for i in all_issues
        ):
            deepseek_assessment = "Ready to Send"
            ai_summary = (
                "The semantic review found no real issues. "
                "The email reads well and is ready to send."
            )

        # Step 6: Determine overall status
        overall_status = self._determine_overall_status(
            rule_results, deepseek_assessment, all_issues
        )

        # Step 7: Build validation summary
        total_checks = len(rule_results) + 1  # rule validators + deepseek
        passed = sum(1 for r in rule_results if r.passed)
        if deepseek_assessment == "Ready to Send":
            passed += 1

        validation_summary = {
            "total_checks": total_checks,
            "passed": passed,
            "issues_found": len(all_issues),
            "rule_engine_results": [
                {
                    "name": r.validator_name,
                    "passed": r.passed,
                    "issues_count": len(r.issues),
                }
                for r in rule_results
            ],
            "deepseek_assessment": deepseek_assessment,
        }

        # Step 8: Build final recommendation
        final_recommendation = self._build_final_recommendation(
            overall_status, all_issues
        )

        return QAReport(
            overall_status=overall_status,
            validation_summary=validation_summary,
            issues=all_issues,
            ai_review_summary=ai_summary,
            final_recommendation=final_recommendation,
        )

    def _filter_harness_false_positives(self, issues: list) -> tuple:
        """
        Remove false positive issues related to Harness pipeline template expressions.

        Harness CI/CD uses <+pipeline.name>, <+pipeline.executionId>, etc. as
        runtime template variables. DeepSeek may incorrectly flag these as
        "unresolved placeholders", "spelling errors", or "coding artifacts".
        This filter catches and removes those issues.

        Returns:
            Tuple of (filtered_issues, count_of_removed_issues).
        """
        filtered = []
        removed = 0
        for issue in issues:
            title = (issue.title or "").lower()
            description = (issue.description or "").lower()

            # Any issue that references a <+...> pattern is a false positive.
            # No legitimate email QA issue would quote <+pipeline.*> syntax.
            if _HARNESS_PATTERN.search(title) or _HARNESS_PATTERN.search(description):
                removed += 1
                continue

            # Catch issues that use placeholder/template language about
            # Harness expressions without directly quoting the <+> syntax
            if _HARNESS_KEYWORDS.search(title) or _HARNESS_KEYWORDS.search(description):
                removed += 1
                continue

            filtered.append(issue)

        return filtered, removed

    def _determine_overall_status(self, rule_results, deepseek_assessment, all_issues):
        """Determine the overall send-readiness status."""
        # Count blocking issues from rule engine
        blocking_issues = [
            i for i in all_issues
            if i.source == "rule_engine" and (
                "missing" in i.title.lower()
                or "no recipient" in i.title.lower()
                or "empty" in i.title.lower()
            )
        ]

        if blocking_issues:
            return "Not Ready to Send"

        if deepseek_assessment == "Not Ready to Send":
            return "Not Ready to Send"

        total_issues = len(all_issues)
        if total_issues >= 5:
            return "Needs Review"
        elif total_issues >= 2:
            return "Needs Review"
        elif total_issues == 0:
            return "Ready to Send"
        else:
            return "Needs Review"

    def _build_final_recommendation(self, overall_status, all_issues):
        """Build a concise final recommendation."""
        if overall_status == "Ready to Send":
            return (
                "This email passes all checks and is ready to send. "
                "A final quick proofread is always recommended before hitting send."
            )
        elif overall_status == "Not Ready to Send":
            critical = [i for i in all_issues if "missing" in i.title.lower()
                        or "empty" in i.title.lower()
                        or "no recipient" in i.title.lower()]
            if critical:
                return (
                    f"This email is not ready to send. Critical issue: "
                    f"{critical[0].title}. {critical[0].recommendation}"
                )
            return (
                "This email is not ready to send. Please address all flagged "
                "issues before sending."
            )
        else:  # Needs Review
            return (
                f"This email needs review before sending. {len(all_issues)} "
                f"issue(s) found. Review each issue, apply the recommendations, "
                f"and re-run the QA check."
            )
