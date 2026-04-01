# llm_service

Python worker for inbox post-processing:
- reads unprocessed inbox rows from PostgreSQL (`e_mails_inbox.operated = false`)
- converts HTML to plain text
- sends text to a configurable local LLM backend (`ollama` or `llama.cpp`)
- prints only validated `is_allowed = true` results

## Classification Output

- The worker calls `llm_connection(text)` for each inbox message.
- `llm_connection` returns either:
  - a normalized contact `dict` with `is_allowed = true`, or
  - `None` (not printed) when the result is invalid or filtered out.
- This means `{"is_allowed": false}` objects are intentionally not printed.

### Validation Rules (post-processing)

- `phone` is mandatory for allowed results.
- If `phone` exists, `full_name` must be present.
- `full_name` is rejected when it is role-based (for example Geschäftsführer/CEO/Inhaber/Vorstand/GF context).
- Placeholder/test values (`test`, `demo`, `sample`, `dummy`, `example`) are rejected.
- Values not present in the original mail text are removed.

### Name Extraction Fallback

If the model does not provide a valid `full_name`, the service tries to infer it from the mail text:
- explicit contact labels (for example `Kontakt:` / `Ansprechpartner:` / `Name:`),
- nearest person-like line above a phone line,
- signature area after `Mit freundlichen Gruessen`.

## Requirements

- Python `>=3.13`
- PostgreSQL with applied migrations from `DB/migrations`
- one local LLM endpoint:
  - Ollama (default): `http://localhost:11434`
  - llama.cpp server: `http://localhost:8080` (OpenAI-compatible API)

## Environment Variables

The service loads `.env` from the repository root.

Required variables:
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`

Optional LLM variables:
- `LLM_BACKEND` (`ollama` default, alternatives: `llama_cpp`, `llama.cpp`)
- `LLM_ENDPOINT` (default `http://localhost:11434` for Ollama, `http://localhost:8080` for llama.cpp)
- `LLM_MODEL` (default `llama3.2:1b`)
- `LLM_TIMEOUT_SECONDS` (default `120`)

Optional Ollama runtime variables (used by Docker Compose):
- `OLLAMA_MODEL` (auto-pulled model, default `llama3.2:1b`)
- `OLLAMA_KEEP_ALIVE` (default `30m`)

## Low-End GPU (NVIDIA Quadro P1000)

Recommended defaults:
- `LLM_MODEL=llama3.2:1b`
- `OLLAMA_MODEL=llama3.2:1b`
- `OLLAMA_KEEP_ALIVE=30m`

Reason:
- Quadro P1000 has limited VRAM (typically 4 GB). 1B models are much more stable and responsive than larger 3B/7B models on this GPU.

## Backend Switch: Ollama <-> llama.cpp

Use Ollama (default):

```powershell
$env:LLM_BACKEND="ollama"
$env:LLM_ENDPOINT="http://localhost:11434"
$env:LLM_MODEL="llama3.2:1b"
```

Use llama.cpp server:

```powershell
$env:LLM_BACKEND="llama_cpp"
$env:LLM_ENDPOINT="http://localhost:8080"
$env:LLM_MODEL="llama3.2:1b"
```

`llama.cpp` server must expose `/v1/chat/completions`.

## Install

From repository root:

```powershell
cd C:\Users\Praktikant\Desktop\MailDirectoryEngine\llm_service
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

## Run

From repository root:

```powershell
python -m llm_service.main
```

## Tests

Unit tests are in `llm_service/tests` and do not require a running database or Ollama server.

```powershell
cd C:\Users\Praktikant\Desktop\MailDirectoryEngine
uv --project llm_service run pytest llm_service/tests -q
```

Run only `DB_adapter` tests:

```powershell
cd C:\Users\Praktikant\Desktop\MailDirectoryEngine
uv --project llm_service run pytest llm_service/tests/test_DB_adapter.py -q
```

`test_DB_adapter.py` covers:
- environment validation (`POSTGRES_*` variables)
- engine creation and injected-engine behavior
- connection and table-reflection error wrapping
- inbox/sent message fetch mapping to `Message`
- `mark_operated` for `Inbox`, `Sent`, and invalid direction
