"""Helpers for extracting project numbers from sent-mail subjects."""

import re


def prj_number_extraction(subject: str) -> str | None:
    """Extract a leading `NN-NNN` style project number from a subject."""

    pattern_prj_number = re.compile(r"^\s*(\d{2}(-|\s)\d{3})")

    m = pattern_prj_number.search(subject)

    if not m:
        return None

    return m.group(1).replace(" ", "-")
