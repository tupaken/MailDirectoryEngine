# MailDirectoryEngine API Documentation

This document describes the current behavior of all implemented methods in the project.

## `src/main.cs`

- `Program.Main(string[] args)`: Console entry point that creates the IMAP engine and database client once, continuously polls inbox and sent folders, processes unseen messages, logs caught exceptions, and keeps running.
- `Program.ComputeHash(string text)`: Returns the SHA-256 hash of `text` as an uppercase hexadecimal string.
- `Program.InboxEMails(ImapEngine engine, DBClientAdapter db, IList<UniqueId> ids)`: Recursively processes inbox UIDs from newest to oldest until a known hash is found, then inserts unseen inbox messages in chronological order.
- `Program.SentEmails(ImapEngine engine, DBClientAdapter db, IList<UniqueId> ids)`: Recursively processes sent-message UIDs from newest to oldest until a known hash is found, exports each unseen sent message as `.eml`, and stores the saved file path with the hash.

## `src/DB/IDBClient.cs`

- `IDBClient.Connection`: Open PostgreSQL connection used by the adapter.
- `IDBClient.SetNewInboxMessage(string hash, string content)`: Persists a new inbox record.
- `IDBClient.CheckHashInbox(string hash)`: Returns `true` when an inbox record with the given hash already exists.
- `IDBClient.SetNewSendMessage(string hash, string path)`: Persists a new sent record.
- `IDBClient.CheckHashSend(string hash)`: Returns `true` when a sent record with the given hash already exists.

## `src/DB/DBClientAdapter.cs`

- `DBClientAdapter.DBClientAdapter()`: Loads `.env` from the repository root when present, builds an `NpgsqlConnection` for `localhost`, opens the database connection immediately, and keeps it available through `Connection`.
- `DBClientAdapter.SetNewInboxMessage(string hash, string content)`: Inserts `hash` and `content` into `e_mails_inbox`.
- `DBClientAdapter.CheckHashInbox(string hash)`: Executes `SELECT EXISTS` against `e_mails_inbox`.
- `DBClientAdapter.SetNewSendMessage(string hash, string path)`: Inserts `hash` and `path` into `e_mails_send`.
- `DBClientAdapter.CheckHashSend(string hash)`: Executes `SELECT EXISTS` against `e_mails_send`.
- `DBClientAdapter.Dispose()`: Disposes the open PostgreSQL connection.

## `src/Imap/ConfigLoader.cs`

- `ConfigLoader.Load(string path)`: Reads JSON from `path` and deserializes it into `ImapSettings` with case-insensitive property names.

## `src/Imap/JsonImapConfigProvider.cs`

- `JsonImapConfigProvider.JsonImapConfigProvider(string path)`: Creates a config provider for a JSON file path.
- `JsonImapConfigProvider.GetConfig(string key)`: Returns account settings for `key` from the JSON file.
- `JsonImapConfigProvider.GetSavePath()`: Resolves save path from JSON `SavePath` or `MAIL_SAVE_DIR` environment variable and returns an absolute path.

## `src/Imap/ImapService.cs`

- `ImapService.ImapService()`: Creates the service with the default `MailKit.Net.Imap.ImapClient` factory.
- `ImapService.ImapService(Func<ImapClient> clientFactory)`: Creates the service with a custom client factory.
- `ImapService.Create(ImapConfig config)`: Creates an IMAP client, connects/authenticates it, and returns it wrapped as `IImapClient`.
- `ImapService.ConnectAndAuthenticate(ImapClient client, ImapConfig config)`: Connects and authenticates a MailKit client using SSL on connect.

## `src/Imap/ImapEngine.cs`

- `ImapEngine.ImapEngine()`: Creates engine defaults (`ImapService`, JSON config file, account key `bewerbung`).
- `ImapEngine.ImapEngine(IImapClientFactory clientFactory, IImapConfigProvider configProvider, string accountKey)`: Creates an engine with custom dependencies.
- `ImapEngine.CreateClient()`: Resolves the configured account and creates a connected, authenticated IMAP client through the configured factory.
- `ImapEngine.ClientDisconnect(IImapClient client)`: Disconnects the IMAP client with `quit=true` and disposes it.
- `ImapEngine.GetLastInboxMessage()`: Returns the latest inbox message as a non-null `MessageDto`; returns a `UniqueId.Invalid` DTO when the inbox is empty.
- `ImapEngine.GetLastSentMail()`: Returns the latest sent message as a non-null `MessageDto`; returns a `UniqueId.Invalid` DTO when the sent folder is empty.
- `ImapEngine.GetAllUIDS(IImapFolder folder)`: Returns all UIDs found by `SearchQuery.All`.
- `ImapEngine.GetAllUIDInbox()`: Opens the inbox in read-only mode, returns all inbox UIDs in server order, and disconnects afterwards.
- `ImapEngine.GetAllUIDSent()`: Opens the resolved sent folder in read-only mode, returns all sent-folder UIDs in server order, and disconnects afterwards.
- `ImapEngine.GetLastUID(IImapFolder fold)`: Returns the last UID in folder search results, or `null` when empty.
- `ImapEngine.GetInbox(IImapClient client)`: Opens the inbox in read-only mode and returns it.
- `ImapEngine.GetSent(IImapClient client)`: Locates the `Gesendete Elemente` folder below the personal root by name or matching full-name suffix, opens it in read-only mode, and throws when no matching sent folder exists.
- `ImapEngine.SaveInboxMail(UniqueId uid)`: Exports an inbox message to `<savePath>/<uid>.eml` and returns the written file path.
- `ImapEngine.SaveSentMail(UniqueId uid)`: Exports a sent message to `<savePath>/<uid>.eml` and returns the written file path.
- `ImapEngine.UseClient<T>(Func<IImapClient, T> action)`: Executes `action` with a newly created IMAP client and guarantees disconnect/dispose in a `finally` block.
- `ImapEngine.GetLatestMessage(IImapFolder folder)`: Loads the newest message from `folder` and returns it as `MessageDto`; returns an empty DTO when the folder has no messages.
- `ImapEngine.CreateMessageDto(UniqueId uid, MimeMessage message)`: Maps a MimeKit message into a lightweight DTO using subject and HTML or text body.
- `ImapEngine.SaveMail(IImapFolder folder, UniqueId uid)`: Writes the specified message to `<savePath>/<uid>.eml` and returns the full file path.
- `ImapEngine.GetSaveDirectory()`: Resolves, normalizes, and creates the configured save directory, then returns the absolute path.
- `ImapEngine.GetInboxMessage(UniqueId id)`: Opens the inbox, loads the requested message by UID, returns it as `MessageDto`, and disconnects afterwards.
- `ImapEngine.GetSentMessage(UniqueId id)`: Opens the resolved sent folder, loads the requested message by UID, returns it as `MessageDto`, and disconnects afterwards.

## Database Schema

- `DB/migrations/V1__init.sql`: Creates `e_mails_inbox` with `id`, `hash`, `content`, `operated`, and `deleted`.
- `DB/migrations/V1__init.sql`: Creates `e_mails_send` with `id`, `hash`, `path`, `operated`, and `deleted`.

## `src/Imap/MailKitImapClientAdapter.cs`

- `MailKitImapClientAdapter.MailKitImapClientAdapter(ImapClient client)`: Wraps a MailKit client.
- `MailKitImapClientAdapter.DirectorySeparator`: Returns the first personal namespace separator.
- `MailKitImapClientAdapter.Inbox`: Returns inbox wrapped as `IImapFolder`.
- `MailKitImapClientAdapter.GetPersonalRoot()`: Returns personal namespace root wrapped as `IImapFolder`.
- `MailKitImapClientAdapter.Disconnect(bool quit)`: Delegates disconnect to MailKit client.
- `MailKitImapClientAdapter.Dispose()`: Delegates dispose to MailKit client.

## `src/Imap/MailKitImapFolderAdapter.cs`

- `MailKitImapFolderAdapter.MailKitImapFolderAdapter(IMailFolder folder)`: Wraps a MailKit folder.
- `MailKitImapFolderAdapter.Name`: Exposes the wrapped folder name.
- `MailKitImapFolderAdapter.FullName`: Exposes the wrapped folder full name.
- `MailKitImapFolderAdapter.Count`: Exposes the wrapped folder message count.
- `MailKitImapFolderAdapter.Open(FolderAccess access)`: Opens folder with requested access.
- `MailKitImapFolderAdapter.GetSubfolders(bool recursive)`: Returns wrapped subfolders.
- `MailKitImapFolderAdapter.Search(SearchQuery query)`: Delegates folder search and returns UIDs.
- `MailKitImapFolderAdapter.GetMessage(UniqueId uid)`: Loads one message by UID.

## Data Contracts

- `ImapConfig`: IMAP account connection and save path settings.
- `ImapSettings`: Root settings with named account dictionary and default save path.
- `MessageDto`: Lightweight message projection (`Uid`, `Titel`, `Context`).
