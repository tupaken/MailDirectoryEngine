# llmService

Python worker for inbox post-processing:
- reads unprocessed inbox rows from PostgreSQL (`e_mails_inbox.operated = false`)
- converts HTML to plain text
- sends text to a configurable local LLM backend (`ollama` or `llama.cpp`)
- maps each valid result to one canonical JSON schema
- enriches phone list from mail text labels (`Telefon`, `Telefax`, `Mobil`, etc.)
- sends contacts to `ContactService` (`POST /api/contacts/canonical`)
- marks inbox rows as `operated = true` only when:
  - contact sync to `ContactService` succeeded, or
  - LLM explicitly returned `is_allowed = false` (irrelevant mail)
- leaves rows unmarked for unclear/failed decisions, so they are retried
- reads unprocessed sent rows from PostgreSQL (`e_mails_send.operated = false`)
- loads the exported `.eml` file, extracts the `Subject`, and parses a leading project number
- forwards matching sent files to `StorageService` with `sourcePath` + `number`
- marks sent rows as `operated = true` when:
  - `StorageService` accepted the payload, or
  - the mail has no `Subject`, or
  - no leading project number is present in the subject
- leaves sent rows unmarked only when subject parsing or storage forwarding fails unexpectedly

## Classification Output

- The worker calls `llm_connection_with_disposition(text)` for each inbox message.
- The decision payload contains:
  - `contacts`: a list of normalized contact dictionaries,
  - `disposition`: one of `relevant`, `irrelevant`, `unknown`.
- Marking behavior:
  - `relevant` + successful sync -> row is marked operated.
  - `irrelevant` (`is_allowed = false`) -> row is marked operated.
  - `unknown` or sync error -> row stays unmarked and is retried.
- Every synced contact is mapped to the shared canonical schema (`schema_version = "1.0"`) and posted to `ContactService`.

## Sent Mail Processing

- `save_sent(...)` processes unoperated `e_mails_send` rows before inbox work in each loop.
- `subject_from_send(path)` reads the `Subject` header from the exported `.eml` file.
- `prj_number_extraction(subject)` matches a leading project number in `NN-NNN` or `NN NNN` form and normalizes spaces to `-`.
- `send_storage_payload(path, number)` posts the file path and project number to `StorageService`.
- Missing `Subject` headers and subjects without a project number are treated as final non-actionable results and are marked operated without retry.
- `StorageService` responses with `404 destination_not_found` are also treated as final and marked operated, because no matching destination folder exists for that project number anymore.
- `StorageService` responses such as `404 source_not_found`, `503 share_unavailable`, or `500 copy_failed` remain retryable and leave the row unoperated.

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

Contact sync variables:
- `CONTACT_SERVICE_ENDPOINT` (default `http://localhost:5000/api/contacts/canonical`)
- `CONTACT_SERVICE_TIMEOUT_SECONDS` (default `30`)
- `CONTACT_SERVICE_API_KEY` (optional, forwarded as `X-Api-Key`)
- `EWS_ACCOUNT_KEY` (default `bewerbung`, forwarded in canonical payload as `account_key`)

Storage sync variables:
- `STORAGE_SERVICE_ENDPOINT` (required for sent-mail forwarding, for example `http://localhost:5001/store`)
- `STORAGE_SERVICE_TIMEOUT_SECONDS` (default `30`)

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
cd C:\Users\Praktikant\Desktop\MailDirectoryEngine\llmService
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

## Run

From repository root:

```powershell
dotnet run --project .\ContactService\ContactsService.csproj
```

In another shell:

```powershell
python -m llmService.main
```

Run with Docker Compose (recommended for full pipeline):

```powershell
docker compose up -d --build
docker compose logs -f llmservice contactservice mailparsing
```

## Tests

Unit tests are in `llmService/tests` and do not require a running database or Ollama server.

```powershell
cd C:\Users\Praktikant\Desktop\MailDirectoryEngine
uv --project llmService run pytest llmService/tests -q
```

Run only `DB_adapter` tests:

```powershell
cd C:\Users\Praktikant\Desktop\MailDirectoryEngine
uv --project llmService run pytest llmService/tests/test_DB_adapter.py -q
```

`test_DB_adapter.py` covers:
- environment validation (`POSTGRES_*` variables)
- engine creation and injected-engine behavior
- connection and table-reflection error wrapping
- inbox/sent message fetch mapping to `Message`
- `mark_operated` for `Inbox`, `Sent`, and invalid direction
