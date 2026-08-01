"""Email Parser — parse raw email text into structured fields."""

import re


def parse_email(raw_text: str) -> dict:
    """
    Parse raw email text into structured components.

    Handles pasted emails from Gmail, Outlook, and plain text.
    No manual field mapping required.
    """
    if not raw_text or not raw_text.strip():
        return {
            "raw": "",
            "sender": "",
            "recipients": [],
            "date": "",
            "subject": "",
            "greeting": "",
            "body": "",
            "closing": "",
            "signature": "",
        }

    text = raw_text.strip()
    lines = text.split("\n")

    sender = ""
    recipients = []
    date = ""
    subject = ""
    header_end_idx = 0

    # --- Try to parse header lines (From:, To:, Date:, Subject:) ---
    # Pattern: "From: Name <email>" or "To: email" etc.
    header_patterns = {
        "from": re.compile(r"^From\s*:\s*(.+)", re.IGNORECASE),
        "to": re.compile(r"^To\s*:\s*(.+)", re.IGNORECASE),
        "cc": re.compile(r"^Cc\s*:\s*(.+)", re.IGNORECASE),
        "date": re.compile(r"^Date\s*:\s*(.+)", re.IGNORECASE),
        "subject": re.compile(r"^Subject\s*:\s*(.+)", re.IGNORECASE),
    }

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        matched = False
        for key, pattern in header_patterns.items():
            m = pattern.match(line_stripped)
            if m:
                value = m.group(1).strip()
                if key == "from":
                    sender = value
                elif key == "to":
                    recipients.extend(_extract_emails(value))
                elif key == "cc":
                    recipients.extend(_extract_emails(value))
                elif key == "date":
                    date = value
                elif key == "subject":
                    subject = value
                matched = True
                header_end_idx = i + 1
                break

        # Stop parsing headers when we hit a line that doesn't match any header
        # and we've already found at least one header, or we see body-like content
        if not matched and (sender or recipients or subject):
            # Check if this looks like body start (e.g., "Dear...", "Hi...")
            if re.match(r"^(Dear|Hi|Hello|Hey|Greetings|Good\s+(morning|afternoon|evening))", line_stripped, re.IGNORECASE):
                header_end_idx = i
                break
            # If we've seen headers and now see non-header content (no colon pattern), stop
            if not re.match(r"^\w+\s*:", line_stripped) and i > 2:
                header_end_idx = i
                break

    # --- Body starts after headers ---
    body_lines = lines[header_end_idx:]
    body_text = "\n".join(body_lines).strip()

    # --- Parse body: greeting, content, closing, signature ---
    greeting = ""
    closing = ""
    signature = ""
    body_content = body_text

    # Common greeting patterns
    greeting_pattern = re.compile(
        r"^(Dear\s+.+?|Hi\s+.+?|Hello\s*.+?|Hey\s+.+?|Greetings\s*.+?|"
        r"Good\s+(morning|afternoon|evening)\s*.+?)(?:[,\n]|$)",
        re.IGNORECASE | re.MULTILINE,
    )

    greeting_match = greeting_pattern.search(body_text)
    if greeting_match:
        greeting = greeting_match.group(0).strip().rstrip("\n")
        # Remove greeting from body
        body_content = body_text[greeting_match.end():].strip()

    # Common closing patterns
    closing_pattern = re.compile(
        r"(?:^|\n)(Thanks(?:&| and)?\s*(?:regards|& Regards)?,?"
        r"|Sincerely,?"
        r"|Best\s+(?:regards|wishes),?"
        r"|Kind\s+regards,?"
        r"|Warm\s+regards,?"
        r"|Regards,?"
        r"|Cheers,?"
        r"|Yours\s+(?:truly|sincerely|faithfully),?"
        r"|Cordially,?"
        r"|Take care,?"
        r"|Talk soon,?"
        r"|All the best,?"
        r"|Best,?"
        r"|Thanks,?)"
        r"\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    closing_matches = list(closing_pattern.finditer(body_content))
    if closing_matches:
        last_closing = closing_matches[-1]
        closing_start = last_closing.start()
        closing = body_content[closing_start:].strip()
        body_content = body_content[:closing_start].strip()

    # Extract signature (lines after closing)
    if closing:
        sig_start = body_text.rfind(closing)
        if sig_start != -1:
            sig_remainder = body_text[sig_start + len(closing):].strip()
            if sig_remainder:
                signature = sig_remainder

    # Clean up body content
    body_content = body_content.strip()

    return {
        "raw": raw_text,
        "sender": sender,
        "recipients": list(dict.fromkeys(recipients)),  # deduplicate preserving order
        "date": date,
        "subject": subject,
        "greeting": greeting,
        "body": body_content,
        "closing": closing,
        "signature": signature,
    }


def _extract_emails(text: str) -> list:
    """Extract email addresses from a header value like 'Name <email>' or 'email'."""
    emails = []
    # Match email addresses
    email_pattern = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    found = email_pattern.findall(text)
    if found:
        emails.extend(found)
    else:
        # If no email found, the whole string might be a plain email
        cleaned = text.strip().strip("<>").strip()
        if "@" in cleaned and " " not in cleaned:
            emails.append(cleaned)
        else:
            # It's probably just a name — use as-is for display
            pass
    return emails
