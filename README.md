# MailDirectoryEngine

A quick command reference for build, run, and tests.

## Prerequisites

- .NET SDK 10 installed (`net10.0`)
- Optional: Docker

Check installed SDKs:

```powershell
dotnet --list-sdks
```

## Setup

Run from the project root:

```powershell
cd C:\Users\Praktikant\Desktop\MailDirectoryEngine
dotnet restore MailDirectoryEngine.slnx
```

## Build

Debug:

```powershell
dotnet build MailDirectoryEngine.slnx -c Debug
```

Release:

```powershell
dotnet build MailDirectoryEngine.slnx -c Release
```

## Run the app

```powershell
dotnet run --project .\MailDirectoryEngine.csproj
```

Note: The app reads configuration from `src/Imap/Imap_config.json`.

## Run tests

All tests:

```powershell
dotnet test MailDirectoryEngine.slnx
```

Test project only:

```powershell
dotnet test .\MailDirectoryEngine.Tests\MailDirectoryEngine.Tests.csproj
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
dotnet clean MailDirectoryEngine.slnx
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
