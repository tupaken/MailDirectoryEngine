# ContactService

`ContactService` is an ASP.NET Core API that accepts canonical contact payloads, creates Exchange contacts through EWS, and persists contact metadata in PostgreSQL.

## Endpoints

### `GET /health`

Returns a simple readiness payload:

```json
{
  "status": "ok"
}
```

### `GET /api/contacts`

Reads contacts from the configured Exchange account.

Query parameters:
- `pageSize`: optional page size between `1` and `500`; defaults to `100`
- `accountKey`: optional logical account key; falls back to `EWS_ACCOUNT_KEY` or `bewerbung`

Successful response shape:

```json
{
  "account_key": "bewerbung",
  "count": 2,
  "items": [
    {
      "id": "AAMk...",
      "displayName": "Max Mustermann"
    }
  ]
}
```

### `POST /api/contacts/canonical`

Creates one Exchange contact from the shared canonical payload used by `llmService`.

Request body example:

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
      { "type": "business", "raw": "+49 30 123456", "e164": "+4930123456" }
    ],
    "address": "Musterstrasse 1, Berlin",
    "website": "muster.de",
    "notes": "Extracted from inbound mail"
  }
}
```

Successful response:

```json
{
  "status": "created",
  "accountKey": "bewerbung",
  "displayName": "Max Mustermann",
  "email": "max@muster.de",
  "phone": "+49 30 123456"
}
```

Validation rules:
- `schema_version` must be `1.0`
- `contact` is required
- either `contact.full_name` or `contact.given_name` + `contact.surname` is required
- `contact.phones` must contain at least one number with `raw` or `e164`

## Ingest Flow

1. Validate the canonical payload.
2. Resolve the EWS account from `account_key`, `EWS_ACCOUNT_KEY`, or the default `bewerbung`.
3. Map the canonical payload into the internal Exchange contact DTO.
4. Check PostgreSQL for an existing contact match by email, phone plus display name, or display name.
5. Create the Exchange contact when no duplicate match exists.
6. Persist contact metadata into the `contacts` table, including `source_message_id` and the created `ews_id`.
7. If metadata persistence fails after the Exchange save, delete the Exchange contact again as a rollback step.

## Environment Variables

The service reads PostgreSQL variables directly from the environment and loads the repository `.env` file for EWS configuration when present.

PostgreSQL:
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST` (defaults to `localhost`)
- `POSTGRES_PORT` (defaults to `5432`)

Account fallback:
- `EWS_ACCOUNT_KEY` optional default account key for requests that do not send `account_key`

EWS account variables are account-specific and use the pattern `EWS__<ACCOUNT_KEY_UPPER>__*`.

Required for every account:
- `EWS__BEWERBUNG__SERVICE_URL`
- `EWS__BEWERBUNG__MAILBOX`
- `EWS__BEWERBUNG__AUTH_MODE` (`oauth` or `basic`)

Required for OAuth mode:
- `EWS__BEWERBUNG__OAUTH_ACCESS_TOKEN`

Required for basic auth mode:
- `EWS__BEWERBUNG__PASSWORD`

Optional for basic auth mode:
- `EWS__BEWERBUNG__USERNAME` (defaults to mailbox)
- `EWS__BEWERBUNG__DOMAIN`

Replace `BEWERBUNG` with the uppercase account key that your deployment uses.

## Database Schema

The service depends on these Flyway migrations:
- `V4__contacts.sql` creates the `contacts` table and JSONB metadata columns
- `V5__ews_item_id.sql` adds the required unique `ews_id` column

## Run

From repository root:

```powershell
dotnet run --project .\ContactService\ContactsService.csproj
```

In Docker Compose, the service listens on `http://localhost:5000`.

## Tests

Run the ContactService test suite with:

```powershell
dotnet test .\ContactService\ContactService.Tests\ContactService.Tests.csproj
```

The test suite covers payload validation, canonical mapping, EWS configuration resolution, Exchange contact engine flow, and the EWS adapter behavior.
