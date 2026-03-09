# MailDirectoryEngine API Documentation

This document describes the current behavior of all implemented methods in the project.

## `src/main.cs`

- `main.Main(string[] args)`: Console entry point that creates an `ImapEngine`, prints inbox/sent information, and exports the latest inbox and sent messages.

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
- `ImapEngine.GetSendCount()`: Returns the message count from the sent folder.
- `ImapEngine.GetInboxCount()`: Returns the message count from the inbox.
- `ImapEngine.GetLastInboxMessage()`: Returns the latest inbox message as `MessageDto`; returns `UniqueId.Invalid` DTO when empty.
- `ImapEngine.GetLastSentMail()`: Returns the latest sent message as `MessageDto`; returns `UniqueId.Invalid` DTO when empty.
- `ImapEngine.GetAllUIDS(IImapFolder folder)`: Returns all UIDs found by `SearchQuery.All`.
- `ImapEngine.GetLastUID(IImapFolder fold)`: Returns the last UID in folder search results, or `null` when empty.
- `ImapEngine.SaveInboxMail(UniqueId uid)`: Exports an inbox message to `<savePath>/<uid>.eml`.
- `ImapEngine.SaveSentMail(UniqueId uid)`: Exports a sent message to `<savePath>/<uid>.eml`.

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
