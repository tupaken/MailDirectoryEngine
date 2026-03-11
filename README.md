# MailDirectoryEngine

A quick command reference for build, run, tests, and database migration.

## Documentation

- API reference (English): `MailParsing/docs/API.md`

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

## Database and Migrations

The repository uses PostgreSQL plus Flyway via `docker-compose.yml`.

- PostgreSQL data is configured through `.env`.
- SQL migration files live in `DB/migrations`.
- `e_mails_inbox` stores inbox message hashes and message content.
- `e_mails_send` stores sent message hashes and the `path` payload written by the application.

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

Important migration rule:
- Do not edit an already applied Flyway migration in shared or persistent databases.
- Add a new file such as `DB/migrations/V2__describe_change.sql` for follow-up schema changes.
- If a local disposable database reports a checksum mismatch, recreate the local database or run `repair` only when the current schema already matches the changed SQL.

## Current Processing Flow

The console entry point in `MailParsing/src/main.cs` currently does the following:

1. Loads the latest inbox message and the latest sent message from IMAP.
2. Computes a SHA-256 hash over each message body.
3. Inserts a new inbox record only when the inbox hash does not already exist in `e_mails_inbox`.
4. Exports the latest sent message and inserts a send record only when the sent hash does not already exist in `e_mails_send`.

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

## Known warnings

- `NU1701` for `Microsoft.Exchange.WebServices 2.2.0` (package is .NET Framework-based).
- `CS8981` for class name `main` in `src/main.cs`.
