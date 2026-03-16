from bs4 import BeautifulSoup

def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)