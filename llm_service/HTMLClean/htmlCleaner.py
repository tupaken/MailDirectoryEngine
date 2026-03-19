from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    """Convert HTML mail bodies into normalized plain text."""

    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)
