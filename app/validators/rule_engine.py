"""Deterministic Rule Engine validators.

All checks here are rule-based — no LLM calls.
"""

import re
from app.validators.models import Issue, ValidationResult


# ── Generic subject words to flag ──────────────────────────────────────────
GENERIC_SUBJECTS = {
    "hello", "hi", "hey", "greetings", "meeting", "question",
    "quick question", "follow up", "update", "urgent", "important",
    "request", "help", "info", "information", "fyi", "checking in",
    "touching base", "ping", "newsletter", "report",
}

APPROPRIATE_GREETINGS = {
    "dear", "hi", "hello", "hey", "greetings",
    "good morning", "good afternoon", "good evening",
}


class SubjectValidator:
    """Check subject line quality using deterministic rules."""

    @staticmethod
    def validate(parsed_email: dict) -> ValidationResult:
        issues = []
        subject = (parsed_email.get("subject") or "").strip()

        # Check: Subject exists
        if not subject:
            issues.append(Issue(
                title="Missing Subject Line",
                description="The email has no subject line.",
                why_it_matters="Emails without subject lines are often ignored, "
                                "mistaken for spam, or deprioritized by recipients.",
                recommendation="Add a concise, descriptive subject line (5–10 words) "
                               "that tells the recipient what the email is about.",
            ))
            return ValidationResult(
                validator_name="Subject Validator",
                passed=False,
                issues=issues,
            )

        # Check: Subject is meaningful (length)
        if len(subject) < 3:
            issues.append(Issue(
                title="Subject Too Short",
                description=f'Subject line is very short: "{subject}".',
                why_it_matters="Overly short subjects lack context and may be ignored.",
                recommendation="Expand the subject to clearly describe the email's purpose.",
            ))

        if len(subject) > 100:
            issues.append(Issue(
                title="Subject Too Long",
                description=f"Subject line is {len(subject)} characters.",
                why_it_matters="Long subjects get cut off in inbox previews.",
                recommendation="Keep the subject under 60 characters for best readability.",
            ))

        # Check: Subject is not generic
        subject_lower = subject.lower().strip().rstrip(".!?")
        if subject_lower in GENERIC_SUBJECTS:
            issues.append(Issue(
                title="Generic Subject Line",
                description=f'Subject "{subject}" is too generic.',
                why_it_matters="Generic subjects don't convey urgency or purpose, "
                                "reducing the chance your email gets opened.",
                recommendation=f"Be specific. Instead of \"{subject}\", "
                               "include what action or topic the email addresses.",
            ))

        # Check: ALL CAPS subject
        if subject.isupper() and len(subject) > 5:
            issues.append(Issue(
                title="Subject in ALL CAPS",
                description="The subject line is written in all capital letters.",
                why_it_matters="ALL CAPS can feel aggressive or like spam.",
                recommendation="Use sentence case or title case for the subject.",
            ))

        passed = len(issues) == 0
        return ValidationResult(
            validator_name="Subject Validator",
            passed=passed,
            issues=issues,
        )


class RecipientValidator:
    """Check recipient fields using deterministic rules."""

    @staticmethod
    def validate(parsed_email: dict) -> ValidationResult:
        issues = []
        recipients = parsed_email.get("recipients") or []

        # Check: At least one recipient
        if not recipients:
            issues.append(Issue(
                title="No Recipients Found",
                description="Could not detect any recipient email addresses.",
                why_it_matters="An email without recipients cannot be delivered.",
                recommendation="Ensure at least one recipient is specified in the To field.",
            ))
            return ValidationResult(
                validator_name="Recipient Validator",
                passed=False,
                issues=issues,
            )

        # Check: Valid email format
        email_regex = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
        invalid = [r for r in recipients if not email_regex.match(r)]
        if invalid:
            issues.append(Issue(
                title="Invalid Recipient Format",
                description=f"The following recipients may be invalid: {', '.join(invalid)}.",
                why_it_matters="Invalid email addresses will bounce, causing delivery failures.",
                recommendation="Verify the email addresses are correct and properly formatted.",
            ))

        # Check: Duplicate recipients
        seen = set()
        dupes = []
        for r in recipients:
            lower = r.lower()
            if lower in seen:
                dupes.append(r)
            seen.add(lower)

        if dupes:
            issues.append(Issue(
                title="Duplicate Recipients",
                description=f"Duplicate recipients found: {', '.join(dupes)}.",
                why_it_matters="Sending duplicate emails annoys recipients and looks unprofessional.",
                recommendation="Remove duplicate recipient entries.",
            ))

        # Check: Large recipient count (potential mass email without BCC)
        if len(recipients) > 10:
            issues.append(Issue(
                title="Many Direct Recipients",
                description=f"{len(recipients)} recipients in the To/Cc field.",
                why_it_matters="Listing many recipients directly exposes their addresses "
                               "and may violate privacy expectations.",
                recommendation="Consider using BCC for mass emails to protect recipient privacy.",
            ))

        passed = len(issues) == 0
        return ValidationResult(
            validator_name="Recipient Validator",
            passed=passed,
            issues=issues,
        )


class GreetingValidator:
    """Check greeting presence and quality using deterministic rules."""

    @staticmethod
    def validate(parsed_email: dict) -> ValidationResult:
        issues = []
        greeting = (parsed_email.get("greeting") or "").strip()
        body = (parsed_email.get("body") or "").strip()

        # Check: Greeting exists
        if not greeting:
            # Check if body starts with a greeting pattern we might have missed
            first_line = body.split("\n")[0].strip() if body else ""
            greeting_words = first_line.lower().split()
            has_greeting_word = any(
                w.rstrip(",.:;") in APPROPRIATE_GREETINGS
                for w in greeting_words[:3]
            ) if greeting_words else False

            if not has_greeting_word:
                issues.append(Issue(
                    title="Missing Greeting",
                    description="No greeting or salutation was detected in the email.",
                    why_it_matters="A greeting sets a respectful tone. Emails without "
                                    "greetings can feel abrupt or demanding.",
                    recommendation="Start with an appropriate greeting like "
                                   "\"Hi [Name],\" or \"Dear [Name],\".",
                ))
            else:
                # We found a greeting-like word — accept it
                greeting = first_line
                parsed_email["greeting"] = first_line

        # Check: Overly casual greeting in formal context (heuristic)
        if greeting:
            greeting_lower = greeting.lower().strip()
            # Check for "Yo", "Sup", "Wassup", "Oi" — too casual
            casual_patterns = [r"\byo\b", r"\bsup\b", r"\bwassup\b", r"\boi\b", r"\bheya\b"]
            for pat in casual_patterns:
                if re.search(pat, greeting_lower):
                    issues.append(Issue(
                        title="Overly Casual Greeting",
                        description=f'Greeting "{greeting}" may be too casual for professional communication.',
                        why_it_matters="Overly casual greetings can undermine your professionalism.",
                        recommendation="Use a more standard greeting: \"Hi\" or \"Hello\" "
                                       "for semi-formal; \"Dear\" for formal.",
                    ))
                    break

            # Check: Generic greeting without name
            generic_greetings = {"hi", "hello", "hey", "dear sir", "dear madam", "dear sir/madam",
                                 "to whom it may concern", "dear all", "hi all", "hello all",
                                 "hi there", "hello there", "hey there", "dear team", "hi team"}
            greeting_clean = greeting_lower.rstrip(",.:;!").strip()
            if greeting_clean in generic_greetings:
                issues.append(Issue(
                    title="Generic Greeting Without Name",
                    description=f'Greeting "{greeting}" doesn\'t address a specific person.',
                    why_it_matters="Personalized greetings build rapport. Generic ones can feel impersonal.",
                    recommendation="Address the recipient by name when possible: "
                                   "\"Hi [Name],\" instead of a generic salutation.",
                ))

        passed = len(issues) == 0
        return ValidationResult(
            validator_name="Greeting Validator",
            passed=passed,
            issues=issues,
        )


class DuplicateContentDetector:
    """Detect repeated content using deterministic text comparison."""

    @staticmethod
    def validate(parsed_email: dict) -> ValidationResult:
        issues = []
        body = (parsed_email.get("body") or "").strip()

        if not body:
            return ValidationResult(
                validator_name="Duplicate Content Detector",
                passed=True,
                issues=[],
            )

        # Split into paragraphs
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", body)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        # Check duplicate paragraphs
        seen_paras = {}
        for i, para in enumerate(paragraphs):
            para_normalized = re.sub(r"\s+", " ", para.lower())
            if len(para_normalized) > 30:
                if para_normalized in seen_paras:
                    issues.append(Issue(
                        title="Repeated Paragraph",
                        description=f"A paragraph appears more than once in the email body.",
                        why_it_matters="Repetition makes emails longer than needed and can "
                                        "confuse the reader about what's important.",
                        recommendation="Remove the duplicate paragraph or consolidate "
                                       "the repeated information.",
                    ))
                    break  # One duplicate paragraph is enough to flag
                seen_paras[para_normalized] = i

        # Check duplicate sentences
        seen_sentences = {}
        for i, sent in enumerate(sentences):
            sent_normalized = re.sub(r"\s+", " ", sent.lower())
            if len(sent_normalized) > 20:
                if sent_normalized in seen_sentences and (i - seen_sentences[sent_normalized]) > 1:
                    issues.append(Issue(
                        title="Repeated Sentence",
                        description=f"A sentence is repeated within the email: \"{sent[:80]}...\"",
                        why_it_matters="Repeated sentences suggest the email wasn't proofread carefully.",
                        recommendation="Remove or rephrase the repeated sentence.",
                    ))
                    break
                seen_sentences[sent_normalized] = i

        passed = len(issues) == 0
        return ValidationResult(
            validator_name="Duplicate Content Detector",
            passed=passed,
            issues=issues,
        )


def run_rule_engine(parsed_email: dict) -> list[ValidationResult]:
    """Run all deterministic validators and return results."""
    validators = [
        SubjectValidator(),
        RecipientValidator(),
        GreetingValidator(),
        DuplicateContentDetector(),
    ]
    results = []
    for validator in validators:
        result = validator.validate(parsed_email)
        results.append(result)
    return results
