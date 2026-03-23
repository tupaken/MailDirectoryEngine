# llm_service

Python worker for inbox post-processing:
- reads unprocessed inbox rows from PostgreSQL (`e_mails_inbox.operated = false`)
- converts HTML to plain text
- sends text to a local Ollama model (`llama3.2`)
- prints the model result

## Requirements

- Python `>=3.13`
- PostgreSQL with applied migrations from `DB/migrations`
- local Ollama endpoint at `http://localhost:11434`

## Environment Variables

The service loads `.env` from the repository root.

Required variables:
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`

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
