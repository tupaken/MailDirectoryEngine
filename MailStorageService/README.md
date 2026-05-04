# MailStorageService

`MailStorageService` is a small ASP.NET Core API that stores exported mail files on a mounted SMB/CIFS share.

## Endpoints

### `GET /health`

Returns a simple readiness payload:

```json
{
  "status": "ok"
}
```

### `POST /store`

Stores an exported mail file for a case number.

Request body:

```json
{
  "sourcePath": "/mail-export/example.eml",
  "number": "12345",
  "targetFileName": "example_renamed"
}
```

`targetFileName` is the destination file name without extension. The service stores the file as `<targetFileName>.eml` in the resolved target directory.

Successful response:

```json
{
  "message": "200"
}
```

Failed responses:

```json
{
  "message": "destination_not_found"
}
```

- `404 Not Found` with `destination_not_found`: no destination folder matches the case number.
- `404 Not Found` with `source_not_found`: the exported `.eml` file path does not exist inside the container.
- `400 Bad Request` with `invalid_target_file_name`: the provided `targetFileName` is empty, contains invalid characters, or contains path segments/traversal sequences (for example `../`).
- `503 Service Unavailable` with `share_unavailable`: the target share could not be mounted/reached.
- `500 Internal Server Error` with `copy_failed`: destination lookup succeeded, but copying still failed after retries.

Use container-visible source paths such as `/mail-export/example.eml`. Windows host paths like `C:\mail-export\example.eml` are not valid inside the container.

## Storage Flow

1. Check whether the configured share is already available at `MOUNT_PATH`.
2. If it is not mounted, try to mount it up to five times.
3. Search below `MOUNT_PATH` for the first top-level directory starting with the given case number.
4. Search below that directory for the first directory containing `DIRECTORY2`.
5. Search below that directory for the first subdirectory whose normalized name contains `DIRECTORY3`.
6. Validate `targetFileName` and build a destination file path inside the resolved directory.
7. Copy the exported file with `rsync -av --partial --inplace`.
8. Retry failed `rsync` copies up to five additional times.

Normalization strips non-alphanumeric characters and compares case-insensitively. This allows folder names such as `Bewerbungen & Lebenslaeufe` to match a configured `DIRECTORY3` value like `Bewerbungen`.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `MOUNT_PATH` | Yes | Local mount target inside the container. |
| `DIRECTORY2` | Yes | Intermediate folder name fragment used during destination lookup. |
| `DIRECTORY3` | Yes | Final folder name fragment matched after normalization. |
| `STORAGE_SKIP_MOUNT` | No | Set to `true`, `1`, or `yes` to skip self-mounting and use an already-mounted path. |
| `SHARE_PATH` | Yes, unless `STORAGE_SKIP_MOUNT=true` | Remote SMB/CIFS share path. |
| `AD_USER` | Yes, unless `STORAGE_SKIP_MOUNT=true` | SMB user name. |
| `AD_PASSWORD` | Yes, unless `STORAGE_SKIP_MOUNT=true` | SMB password. |
| `AD_DOMAIN` | Yes, unless `STORAGE_SKIP_MOUNT=true` | SMB domain. |
| `AD_VERS` | Yes, unless `STORAGE_SKIP_MOUNT=true` | SMB protocol version passed to `mount -t cifs`. |
| `SEC` | Yes, unless `STORAGE_SKIP_MOUNT=true` | SMB security mode passed to `mount -t cifs`. |
| `UID` | Yes, unless `STORAGE_SKIP_MOUNT=true` | User ID used for the mounted share. |
| `GID` | Yes, unless `STORAGE_SKIP_MOUNT=true` | Group ID used for the mounted share. |

## Run

From repository root:

```powershell
dotnet run --project .\MailStorageService\MailStorageService.csproj
```

In Docker Compose, the service listens on `http://localhost:5001` and receives the `/mail-export` bind mount that `llmService` references in storage requests.

## Testing

Run the storage service tests with:

```powershell
dotnet test MailStorageService\MailStorageService.Tests\MailStorageService.Tests.csproj
```

The test suite covers mount checks, destination resolution, retry behavior, and the HTTP endpoint handlers.
