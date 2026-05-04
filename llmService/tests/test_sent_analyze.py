"""Unit tests for sent-mail subject and context analysis helpers."""

from llmService.LLM import sent_analyze as sent_module
from llmService.LLM.sent_analyze import prj_number_extraction, sent_filename_extraction


def test_prj_number_extraction_normalizes_space_separated_prefix():
    """Subjects with a leading space-separated project number should normalize to hyphen."""

    assert prj_number_extraction(" 12 345 Angebot") == "12-345"


def test_prj_number_extraction_returns_none_without_leading_project_number():
    """Subjects without a leading project number should not produce a match."""

    assert prj_number_extraction("Angebot 12 345") is None


def test_sent_filename_extraction_parses_json_response(monkeypatch):
    """The sent-context LLM response should provide the storage target name."""

    monkeypatch.setattr(
        sent_module,
        "generate_prompt_response",
        lambda prompt: '{"target_file_name": "Rueckfrage zur Terminabstimmung"}',
    )

    result = sent_filename_extraction("Bitte bestaetigen Sie den Termin morgen.")

    assert result == "Rueckfrage zur Terminabstimmung"


def test_sent_filename_extraction_returns_unknown_for_non_json_response(monkeypatch):
    """Plain-text LLM responses should not be accepted as structured filenames."""

    monkeypatch.setattr(
        sent_module,
        "generate_prompt_response",
        lambda prompt: "Rueckfrage zur Terminabstimmung",
    )

    result = sent_filename_extraction("Bitte bestaetigen Sie den Termin morgen.")

    assert result == "unknown"


def test_sent_filename_extraction_shortens_overlong_name(monkeypatch):
    """Overlong names should trigger the shortener prompt and use its JSON result."""

    responses = iter(
        [
            '{"target_file_name": "Sehr langer Dateiname fuer die ausfuehrliche Rueckfrage zur Terminabstimmung und Projektklaerung"}',
            '{"target_file_name": "Rueckfrage zur Terminabstimmung"}',
        ]
    )

    monkeypatch.setattr(
        sent_module,
        "generate_prompt_response",
        lambda prompt: next(responses),
    )

    result = sent_filename_extraction("Bitte bestaetigen Sie den Termin morgen.")

    assert result == "Rueckfrage zur Terminabstimmung"
