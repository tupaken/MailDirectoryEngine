"""Helpers for extracting project numbers from sent-mail subjects."""

import re
import json
from llmService.API.LlmBackendClient import generate_prompt_response
from .promptSent import _PROMPT_SENT,_PROMPT_SHORTEN_SENT_FILENAME

PROJECT_NUMBER_PREFIX_RE = re.compile(r"^\s*(\d{2}[-\s]\d{3})")


def prj_number_extraction(subject: str) -> str | None:
    """Extract a leading `NN-NNN` style project number from a subject."""

    m = PROJECT_NUMBER_PREFIX_RE.search(subject)

    if not m:
        return None

    return m.group(1).replace(" ", "-")


def sent_filename_extraction(context:str)->str:
    """Generate a target name from cleaned sent-mail context."""


    if not context or not context.strip():
        return "unknown"
    
    prompt=_PROMPT_SENT.format(EMAIL_CONTEXT=context.strip())
    raw_response = generate_prompt_response(prompt)
    result= _parse_target_file_name_response(raw_response)

    return result

def _parse_target_file_name_response(raw_response:str)->str:
    """Extract the target file name from the LLM JSON response."""

    if not raw_response:
        return "unknown"
    
    match = re.search(r"\{.*\}",raw_response,flags=re.DOTALL)


    if not match:
        return "unknown"
    

    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return "unknown"
    
    target_file_name = payload.get("target_file_name")
    
    if not isinstance(target_file_name,str):
        return "unknown"
    
    if len(target_file_name)>60:
        target_file_name=_shorten_target_file_name(target_file_name)
    
    return target_file_name.strip() or "unknown"


def _shorten_target_file_name(target_file_name: str) -> str:
    """Ask the LLM to shorten an overlong target file name."""

    prompt = _PROMPT_SHORTEN_SENT_FILENAME.format(
        TARGET_FILE_NAME=target_file_name.strip()
    )

    raw_response = generate_prompt_response(prompt)
    result = _parse_target_file_name_response(raw_response)

    return result if result != "unknown" else target_file_name[:60].strip()
