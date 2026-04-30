"""HTML sanitizing helpers for converting emails into plain text."""

from email import policy
from email.parser import BytesParser
from email.message import EmailMessage
import re

from bs4 import BeautifulSoup

BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}


def html_to_text(html: str) -> str:
    """Convert HTML mail bodies into normalized plain text."""

    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    for br_tag in soup.find_all("br"):
        br_tag.replace_with("\n")

    for block_tag in soup.find_all(BLOCK_TAGS):
        block_tag.append("\n")

    text = soup.get_text(" ", strip=False).replace("\xa0", " ")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)

    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if re.fullmatch(r"[\s<>\"']+", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def subject_from_send(email: str) -> str | None:
    """Read the Subject header from a raw `.eml` file on disk."""

    msg=_get_msg(email)


    return msg.get("Subject")

def content_from_send(email: str)-> str | None:
    """Read the Content from a raw `.eml` file on disk."""

    msg=_get_msg(email)

    return msg.get_content()


def _get_msg(email:str)->EmailMessage:
     
    with open(email, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    return msg