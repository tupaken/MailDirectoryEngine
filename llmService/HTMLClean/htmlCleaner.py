"""HTML sanitizing helpers for converting emails into plain text."""

from email import policy
from email.parser import BytesParser
import re

from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    """Convert HTML mail bodies into normalized plain text."""

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if re.fullmatch(r"[\s<>\"']+", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def subject_from_send(email: str) -> str | None:
    """Read the Subject header from a raw `.eml` file on disk."""

    with open(email, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    return msg.get("Subject")
