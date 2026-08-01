"""DeepSeek API integration for semantic email review."""

import json
import re
import requests
from app.config import Config
from app.validators.models import Issue


def review_with_deepseek(parsed_email: dict) -> dict:
    """
    Send email to DeepSeek for semantic review.

    Returns structured review covering: grammar, spelling, clarity,
    professionalism, call-to-action quality, and overall assessment.
    """
    api_key = Config.DEEPSEEK_API_KEY

    if not api_key or api_key.startswith("sk-your-"):
        return _mock_review(parsed_email)

    # Build the email text for review
    email_text = _format_email_for_review(parsed_email)
    if not email_text.strip():
        return {
            "issues": [],
            "summary": "No email content to review.",
            "overall_assessment": "Not Ready to Send",
        }

    prompt = _build_review_prompt(email_text)

    try:
        response = requests.post(
            Config.DEEPSEEK_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": Config.DEEPSEEK_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert email QA reviewer. Your job is to review "
                            "emails and identify issues with grammar, spelling, clarity, "
                            "professionalism, tone, and call-to-action quality. "
                            "Return ONLY valid JSON — no markdown, no explanation, "
                            "no code fences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Parse JSON from response — handle code fences if present
        json_str = content
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if fence_match:
            json_str = fence_match.group(1)

        review_data = json.loads(json_str)
        return review_data

    except requests.RequestException as e:
        return {
            "issues": [],
            "summary": f"DeepSeek API error: {str(e)}",
            "overall_assessment": "Needs Review",
        }
    except json.JSONDecodeError:
        return {
            "issues": [],
            "summary": "Failed to parse DeepSeek response. Please try again.",
            "overall_assessment": "Needs Review",
        }


def _format_email_for_review(parsed_email: dict) -> str:
    """Format parsed email fields into a text block for review."""
    parts = []
    if parsed_email.get("subject"):
        parts.append(f"Subject: {parsed_email['subject']}")
    if parsed_email.get("recipients"):
        parts.append(f"To: {', '.join(parsed_email['recipients'])}")
    if parsed_email.get("greeting"):
        parts.append(f"Greeting: {parsed_email['greeting']}")
    if parsed_email.get("body"):
        parts.append(f"Body:\n{parsed_email['body']}")
    if parsed_email.get("closing"):
        parts.append(f"Closing: {parsed_email['closing']}")
    if parsed_email.get("signature"):
        parts.append(f"Signature: {parsed_email['signature']}")
    return "\n\n".join(parts)


def _build_review_prompt(email_text: str) -> str:
    """Build the review prompt for DeepSeek."""
    return f"""Review the following email and return a structured JSON assessment.

## Email to Review:
```
{email_text}
```

## Review Instructions:
Evaluate the email on these dimensions and flag any issues:

1. **Grammar**: Check for grammatical errors, tense issues, subject-verb agreement.
2. **Spelling**: Check for spelling mistakes and typos.
3. **Clarity**: Is the message clear and easy to understand? Flag confusing sentences.
4. **Professionalism**: Is the tone appropriate for a professional setting?
5. **Call-to-Action (CTA)**: Is the next expected action clearly communicated? Does the recipient know what to do?
6. **Tone**: Is the tone respectful and appropriate?
7. **Overall**: Would you recommend sending this email as-is?

## Required JSON Format:
{{
  "issues": [
    {{
      "title": "Brief issue title",
      "description": "What the issue is, with specific examples from the email",
      "why_it_matters": "Why this issue should be fixed before sending",
      "recommendation": "Specific, actionable fix"
    }}
  ],
  "summary": "2-4 sentence summary of the email's quality, highlighting the most important concern (or confirming it's good to send)",
  "overall_assessment": "Ready to Send" | "Needs Review" | "Not Ready to Send"
}}

## Rules:
- Only flag REAL issues that affect communication quality. If something is fine, don't invent problems.
- Be specific — quote the problematic text in descriptions.
- Recommendations must be actionable.
- If the email is excellent with no issues, return an empty issues array and "Ready to Send".
- DO NOT rewrite the entire email — only point out specific issues.
- Return ONLY the JSON object, no other text.
- Template expressions in the format <+...> (e.g., <+pipeline.name>, <+pipeline.executionId>, <+pipeline.triggeredBy.name>, <+pipeline.startTs>, <+pipeline.executionUrl>) are valid Harness CI/CD pipeline variables that resolve at runtime. Do NOT flag these as issues, placeholders, or spelling errors — they are intentional and will be replaced with actual values before the email is sent.
- Do NOT flag minor signature formatting — spacing around colons, emoji vs text labels, inconsistent contact detail styles (e.g., "GitHub : link" vs "📧 email"). These are personal style choices, not real issues. Only flag the signature if it is missing entirely when one is expected.
- Focus on what matters: grammar, spelling, clarity, tone, CTA, and missing critical elements (subject, greeting, recipient). Skip trivial formatting nitpicks.
"""


def _mock_review(parsed_email: dict) -> dict:
    """
    Mock review for development/demo when no API key is set.
    Performs basic heuristic checks so the app is functional without DeepSeek.
    """
    issues = []
    body = (parsed_email.get("body") or "").strip()
    greeting = (parsed_email.get("greeting") or "").strip()
    subject = (parsed_email.get("subject") or "").strip()

    sentiment = "neutral"
    assessment = "Ready to Send"

    # Basic heuristic checks
    if not body:
        return {
            "issues": [{
                "title": "Empty Email Body",
                "description": "The email body is empty.",
                "why_it_matters": "An email without a body cannot convey your message.",
                "recommendation": "Write the email content before sending.",
            }],
            "summary": "The email body is empty and cannot be sent.",
            "overall_assessment": "Not Ready to Send",
        }

    # Heuristic: body too short
    if len(body.split()) < 10:
        issues.append({
            "title": "Very Short Email",
            "description": f"The email body is only {len(body.split())} words long.",
            "why_it_matters": "Very short emails may lack context and come across as abrupt.",
            "recommendation": "Add more context or detail to ensure the message is clear.",
        })
        sentiment = "brief"
        assessment = "Needs Review"

    # Heuristic: body too long
    if len(body.split()) > 2000:
        issues.append({
            "title": "Very Long Email",
            "description": f"The email body is {len(body.split())} words — quite lengthy.",
            "why_it_matters": "Very long emails may not be read fully. Key points can get lost.",
            "recommendation": "Consider summarizing or using bullet points for clarity. "
                              "If detailed information is needed, consider an attachment.",
        })
        sentiment = "long"
        if assessment == "Ready to Send":
            assessment = "Needs Review"

    # Heuristic: check for common typos
    common_typos = {
        "recieve": "receive", "seperate": "separate", "definately": "definitely",
        "accomodate": "accommodate", "occured": "occurred", "untill": "until",
        "alot": "a lot", "your welcome": "you're welcome",
        "there" : None, "their": None, "theyre": "they're",
    }
    body_lower = body.lower()
    for typo, correction in common_typos.items():
        if typo in body_lower:
            issues.append({
                "title": "Potential Spelling Error",
                "description": f'Found "{typo}" in the email.'
                               + (f' Did you mean "{correction}"?' if correction else ""),
                "why_it_matters": "Spelling errors reduce credibility.",
                "recommendation": f'Review and correct "{typo}"'
                                   + (f' to "{correction}".' if correction else "."),
            })
            break  # One typo flag is enough for mock

    # Heuristic: check for extreme punctuation (multiple !!! or ???)
    if re.search(r"[!?]{3,}", body):
        issues.append({
            "title": "Excessive Punctuation",
            "description": "Multiple exclamation or question marks found (e.g., \"!!!\" or \"???\").",
            "why_it_matters": "Excessive punctuation can appear unprofessional or emotionally charged.",
            "recommendation": "Use a single punctuation mark for a more professional tone.",
        })
        if assessment == "Ready to Send":
            assessment = "Needs Review"

    # Heuristic: CTA check — look for action-oriented language
    cta_patterns = [
        r"please\s+(review|approve|confirm|check|send|reply|respond|let\s+me\s+know|find|see)",
        r"(review|approve|confirm|check|send|reply|respond)\s+(please|by|before|at|as)",
        r"(let\s+me\s+know|waiting\s+for|looking\s+forward)",
        r"(deadline|due\s+by|by\s+\w+\s+\d+)",
        r"(RSVP|action\s+(required|needed)|urgent)",
    ]
    has_cta = any(re.search(pat, body, re.IGNORECASE) for pat in cta_patterns)
    if not has_cta:
        issues.append({
            "title": "Unclear Call-to-Action",
            "description": "The email doesn't clearly state what action the recipient should take.",
            "why_it_matters": "Without a clear CTA, the recipient may not know what to do next, "
                              "leading to delays or inaction.",
            "recommendation": "Add a clear next step: \"Please review by Friday\", "
                              "\"Can you confirm?\", or \"Let me know your thoughts.\"",
        })
        if assessment == "Ready to Send":
            assessment = "Needs Review"

    # Build summary
    if not issues:
        summary = (
            "The email appears well-written. No major issues were detected in the "
            "automated review. The tone, structure, and call-to-action appear appropriate. "
            "Consider a final manual proofread before sending."
        )
    else:
        issue_titles = [i["title"] for i in issues]
        if len(issues) == 1:
            summary = f"One issue was found: {issue_titles[0]}. Review and fix before sending."
        else:
            summary = f"{len(issues)} issues were found: {', '.join(issue_titles)}. Address these before sending."

    return {
        "issues": issues,
        "summary": summary,
        "overall_assessment": assessment,
    }
