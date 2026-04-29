"""Helpers for extracting project numbers from sent-mail subjects."""

import re

PROJECT_NUMBER_PREFIX_RE = re.compile(r"^\s*(\d{2}[-\s]\d{3})")


def prj_number_extraction(subject: str) -> str | None:
    """Extract a leading `NN-NNN` style project number from a subject."""

    m = PROJECT_NUMBER_PREFIX_RE.search(subject)

    if not m:
        return None

    return m.group(1).replace(" ", "-")
