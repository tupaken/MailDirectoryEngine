"""Unit tests for sent-mail subject analysis helpers."""

from llmService.LLM.sent_analyze import prj_number_extraction


def test_prj_number_extraction_normalizes_space_separated_prefix():
    """Subjects with a leading space-separated project number should normalize to hyphen."""

    assert prj_number_extraction(" 12 345 Angebot") == "12-345"


def test_prj_number_extraction_returns_none_without_leading_project_number():
    """Subjects without a leading project number should not produce a match."""

    assert prj_number_extraction("Angebot 12 345") is None
