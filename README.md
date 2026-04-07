# MailDirectoryEngine

A quick command reference for build, run, tests, and database migration.

## Documentation

- API reference (English): `MailParsing/docs/API.md`
- Runtime configuration overview: see `MailParsing/src/Imap/Imap_config.json`
- Python worker documentation: `llmService/README.md`

## Prerequisites

- .NET SDK 10 installed (`net10.0`)
- Optional: Docker

Check installed SDKs:

```powershell
dotnet --list-sdks
```

## Setup

Run from the repository root:

```powershell
cd C:\Users\Praktikant\Desktop\MailDirectoryEngine
dotnet restore .\MailParsing\MailDirectoryEngine.slnx
```

## Build

Debug:

```powershell
dotnet build .\MailParsing\MailDirectoryEngine.slnx -c Debug
```

Release:

```powershell
dotnet build .\MailParsing\MailDirectoryEngine.slnx -c Release
```

## Run the app

```powershell
dotnet run --project .\MailParsing\MailDirectoryEngine.csproj
```

Notes:
- The app reads IMAP configuration from `MailParsing/src/Imap/Imap_config.json`.
- Database credentials are loaded from `.env`.
- The current `Main` implementation runs in a continuous polling loop and retries after logged exceptions without exiting.

## Run ContactService API

```powershell
dotnet run --project .\ContactService\ContactsService.csproj
```

Notes:
- Health endpoint: `GET http://localhost:5000/health`
- Canonical contact ingest endpoint: `POST http://localhost:5000/api/contacts/canonical`
- Optional list endpoint: `GET http://localhost:5000/api/contacts?pageSize=100`

Canonical ingest payload example:

```json
{
  "schema_version": "1.0",
  "account_key": "bewerbung",
  "source_message_id": "12345",
  "contact": {
    "full_name": "Max Mustermann",
    "company": "Muster GmbH",
    "email": "max@muster.de",
    "phones": [
      { "type": "business", "raw": "+49 30 123456", "e164": "+4930123456" },
      { "type": "fax", "raw": "+49 30 123457", "e164": "+4930123457" }
    ],
    "address": "Musterstrasse 1, Berlin",
    "website": "muster.de"
  }
}
```

## Run Full Stack With Docker Compose

Start all services (PostgreSQL, migration, MailParsing, ContactService, llmService, Adminer, Ollama):

```powershell
docker compose up -d --build
```

Watch logs:

```powershell
docker compose logs -f mailparsing llmservice contactservice
```

Stop everything:

```powershell
docker compose down
```

Notes:
- Inside Compose, service-to-service URLs are preconfigured:
  - PostgreSQL host: `postgres`
  - Contact API: `http://contactservice:5000/api/contacts/canonical`
  - Ollama: `http://ollama:11434`
- Mail exports are written to `./mail-export` on the host.

## IMAP Configuration

The engine expects a JSON file at `MailParsing/src/Imap/Imap_config.json` with named accounts plus a default export directory.

Example:

```json
{
  "accounts": {
    "bewerbung": {
      "host": "imap.example.test",
      "port": 993,
      "user": "user@example.test",
      "password": "secret"
    }
  },
  "savePath": "C:\\mail-export"
}
```

Notes:
- `accounts` is a dictionary. The current production default key is `bewerbung`.
- `savePath` is used for `.eml` exports. If it is empty, `MAIL_SAVE_DIR` is used as a fallback.
- Keep real credentials out of committed example files when possible.

## Database and Migrations

The repository uses PostgreSQL plus Flyway via `docker-compose.yml`.

- PostgreSQL data is configured through `.env`.
- SQL migration files live in `DB/migrations`.
- `e_mails_inbox` stores inbox message hashes, message content, and an `account` scope value.
- `e_mails_send` stores sent message hashes, exported `path`, and an `account` scope value.
- Current deduplication constraints are account-scoped: `UNIQUE(hash, account)` on both tables.

Start the database:

```powershell
docker compose up -d postgres
```

Run migrations:

```powershell
docker compose run --rm migrate
```

Optional database UI:

```powershell
docker compose up -d adminer
```

Start Ollama with GPU and auto-pull configured model:

```powershell
docker compose up -d ollama ollama-init
```

Check available models:

```powershell
docker compose exec ollama ollama list
```

Important migration rule:
- Do not edit an already applied Flyway migration in shared or persistent databases.
- Add a new file such as `DB/migrations/V2__describe_change.sql` for follow-up schema changes.
- If a local disposable database reports a checksum mismatch, recreate the local database or run `repair` only when the current schema already matches the changed SQL.

## Current Processing Flow

The console entry point in `MailParsing/src/main.cs` currently does the following:

1. Creates one database adapter, creates an IMAP engine per configured user key, and then enters an endless processing loop.
2. For each engine, loads all inbox UIDs and recursively walks from newest to oldest until an already known `(hash, account)` combination is found.
3. Inserts each unseen inbox message body into `e_mails_inbox` in chronological order with the current account value.
4. Loads all sent-message UIDs and recursively walks from newest to oldest until an already known `(hash, account)` combination is found.
5. Exports each unseen sent message to `<savePath>/<uid>_<random6>.eml` and stores the hash, path, and account in `e_mails_send`.
6. Logs exceptions to the console and immediately continues with the next loop iteration.

## Run tests

All tests:

```powershell
dotnet test .\MailParsing\MailDirectoryEngine.slnx
```

Test project only:

```powershell
dotnet test .\MailParsing\MailDirectoryEngine.Tests\MailDirectoryEngine.Tests.csproj
```

Single test (example):

```powershell
dotnet test --filter "FullyQualifiedName~ImapServiceTests.Create_WrapsAuthException_InInvalidOperationException"
```

Single test class:

```powershell
dotnet test --filter "FullyQualifiedName~ImapEngineTests"
```

With detailed output and TRX log:

```powershell
dotnet test -v normal --logger "trx;LogFileName=test-results.trx"
```

If a local `MailDirectoryEngine.exe` instance is already running from the same build output, stop it before running tests so MSBuild can overwrite the binaries.

## Clean

```powershell
dotnet clean .\MailParsing\MailDirectoryEngine.slnx
```

## Docker

Build image:

```powershell
docker build -t maildirectoryengine:local .
```

Run container:

```powershell
docker run --rm maildirectoryengine:local
```

## LLM Runtime (Ollama / llama.cpp)

The Python worker (`llmService`) reads these root `.env` variables:
- `LLM_BACKEND` (`ollama` or `llama_cpp`)
- `LLM_ENDPOINT`
- `LLM_MODEL`

For low-end GPUs like NVIDIA Quadro P1000, use small models:
- `LLM_MODEL=llama3.2:1b`
- `OLLAMA_MODEL=llama3.2:1b`

To switch to `llama.cpp`, run an OpenAI-compatible server and set:

```powershell
$env:LLM_BACKEND="llama_cpp"
$env:LLM_ENDPOINT="http://localhost:8080"
$env:LLM_MODEL="llama3.2:1b"
```

## Known warnings

- `NU1701` for `Microsoft.Exchange.WebServices 2.2.0` (package is .NET Framework-based).
- `CS8981` for class name `main` in `src/main.cs`.
