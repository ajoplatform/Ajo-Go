import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class WhatsAppParseResult:
    amount: Optional[int]
    sender: Optional[str]
    confidence: float
    needs_review: bool
    raw_line: str


def parse_line(line: str) -> Optional[WhatsAppParseResult]:
    line = line.strip()
    if not line:
        return None

    sender = None
    message = None

    # WhatsApp format: "12/03/2025, 08:30 - Name: message"
    wa_match = re.match(
        r"^\d{1,2}/\d{1,2}/\d{4},\s+\d{1,2}:\d{2}\s*-\s*([^:]+):\s*(.+)$", line
    )
    if wa_match:
        sender = wa_match.group(1).strip()
        message = wa_match.group(2).strip()
    elif ":" in line:
        parts = line.split(":", 1)
        sender = parts[0].strip()
        message = parts[1].strip() if len(parts) > 1 else ""

    if not sender or not message:
        return None

    # Third-person: "Reghie: Mary 3000" -> sender=Mary, amount=3000
    # Check before amount extraction since "Mary 3000" looks like sender+amount
    tp_match = re.match(r"^([A-Za-z][A-Za-z\s]{1,20})\s+(\d[\d,]*\.?\d*)$", message)
    if tp_match:
        potential = tp_match.group(1).strip()
        # Make sure it's not a keyword
        if potential.lower() not in ("paid", "contributed", "transferred"):
            sender = potential
            message = tp_match.group(2).strip()
            amount, _ = extract_amount(message)
            if amount:
                return WhatsAppParseResult(
                    amount=amount,
                    sender=sender,
                    confidence=0.7,
                    needs_review=True,
                    raw_line=line,
                )

    # Extract amount from message
    amount, confidence = extract_amount(message)
    if amount is None or amount <= 0:
        return None

    return WhatsAppParseResult(
        amount=amount,
        sender=sender,
        confidence=confidence,
        needs_review=confidence < 0.7,
        raw_line=line,
    )


def extract_amount(text: str):
    text = text.strip()

    explicit_patterns = [
        (r"paid\s*(?:N|n)?([\d,]+(?:\.\d{2})?)", 0.95),
        (r"contributed\s*(?:N|n)?([\d,]+(?:\.\d{2})?)", 0.95),
        (r"transferred\s*(?:N|n)?([\d,]+(?:\.\d{2})?)", 0.90),
    ]
    for pattern, conf in explicit_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                amt = int(float(m.group(1).replace(",", "")))
                if amt > 0:
                    return amt, conf
            except ValueError:
                pass

    m = re.match(r"^(\d[\d,]*\.?\d*)$", text)
    if m:
        try:
            amt = int(float(m.group(1).replace(",", "")))
            if amt > 0:
                return amt, 0.5
        except ValueError:
            pass

    m = re.search(r"(?:N|n)?([\d,]+)", text)
    if m:
        try:
            amt = int(float(m.group(1).replace(",", "")))
            if amt > 0:
                return amt, 0.3
        except ValueError:
            pass

    return None, 0.0


def parse_file(content: str) -> list[WhatsAppParseResult]:
    if content.startswith("\ufeff"):
        content = content[1:]

    results = []
    for line in content.split("\n"):
        result = parse_line(line)
        if result:
            results.append(result)
    return results
