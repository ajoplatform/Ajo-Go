import re
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class WhatsAppParseResult:
    amount: Optional[int]
    sender: Optional[str]
    confidence: float
    needs_review: bool
    raw_line: str


@dataclass
class WhatsAppPost:
    sender: str
    content: str
    post_type: str  # "payment", "collection", "order", "rule", "message"
    timestamp: datetime
    raw_members: List[dict]
    raw_line: str

    def to_dict(self):
        return {
            "sender": self.sender,
            "content": self.content,
            "post_type": self.post_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "raw_members": self.raw_members,
            "raw_line": self.raw_line,
        }


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


def detect_post_type(content: str) -> str:
    """Auto-detect post type from message content"""
    content_lower = content.lower()
    if "*" in content and "payment" in content_lower:
        return "payment"
    elif "*" in content and "collection" in content_lower:
        return "collection"
    elif "*" in content and "order" in content_lower:
        return "order"
    elif "rules" in content_lower or "rule" in content_lower:
        return "rule"
    return "message"


def parse_whatsapp_timestamp(line: str) -> Optional[datetime]:
    """Extract timestamp from WhatsApp message line"""
    match = re.match(r"^\[(\d{1,2}/\d{1,2}/\d{4}),\s+(\d{1,2}:\d{2}:\d{2})\]", line)
    if match:
        try:
            date_str, time_str = match.groups()
            dt = datetime.strptime(f"{date_str},{time_str}", "%d/%m/%Y,%H:%M:%S")
            return dt
        except ValueError:
            pass
    return None


def extract_member_list(lines: List[str], start_idx: int) -> List[dict]:
    """Extract member list from lines starting at index"""
    members = []
    i = start_idx
    max_lines = 20  # Limit to prevent reading too far

    while i < len(lines) and max_lines > 0:
        line = lines[i].strip()
        if not line:
            i += 1
            max_lines -= 1
            continue

        # Stop at emoji lines (❌❌❌ or ✅✅✅)
        if re.match(r"^[❌✅]+\s*$", line):
            break

        # Stop at new WhatsApp message line
        if re.match(r"^\[\d{1,2}/\d{1,2}/\d{4},", line):
            break

        # Skip audio/image/sticker omitted
        if "omitted" in line.lower():
            i += 1
            max_lines -= 1
            continue

        # Match numbered list: "1. Name" or "1   Name"
        match = re.match(r"^(\d+)[.\s]+(.+)$", line)
        if match:
            position = int(match.group(1))
            name = match.group(2).strip()

            # Check if next line has checkmark (on same position block)
            received = False
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if "✅" in next_line:
                    received = True

            # Avoid duplicates
            if not members or name != members[-1].get("name"):
                members.append(
                    {
                        "name": name,
                        "position": position,
                        "received_payout": received,
                    }
                )
        i += 1
        max_lines -= 1

    return members


def parse_whatsapp_posts(content: str) -> List[WhatsAppPost]:
    """Parse WhatsApp export and extract all message types"""
    if content.startswith("\ufeff"):
        content = content[1:]

    posts = []
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Try to match WhatsApp message format
        wa_match = re.match(
            r"^\[(\d{1,2}/\d{1,2}/\d{4}),\s+(\d{1,2}:\d{2}:\d{2})\]\s*([^:]+):\s*(.+)$",
            line,
            re.UNICODE,
        )

        if wa_match:
            timestamp = None
            try:
                date_str, time_str = wa_match.group(1), wa_match.group(2)
                timestamp = datetime.strptime(
                    f"{date_str},{time_str}", "%d/%m/%Y,%H:%M:%S"
                )
            except ValueError:
                pass

            sender = wa_match.group(3).strip()
            message = wa_match.group(4).strip()

            # Detect post type
            post_type = detect_post_type(message)

            # Look for member list in following lines
            raw_members = []
            if post_type in ("payment", "collection", "order"):
                raw_members = extract_member_list(lines, i + 1)

            posts.append(
                WhatsAppPost(
                    sender=sender,
                    content=message,
                    post_type=post_type,
                    timestamp=timestamp,
                    raw_members=raw_members,
                    raw_line=line,
                )
            )

        i += 1

    return posts
