using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using MailDirectoryEngine.src.Imap;
using MailKit;
using MailKit.Search;
using MimeKit;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class ImapEngineTests
{
    /// <summary>
    /// Verifies that the public IMAP engine constructor creates an instance.
    /// </summary>
    [Fact]
    public void Constructor_CreatesInstance()
    {
        var engine = new ImapEngine("bewerbung", "ACCOUNT_HASH");
        Assert.NotNull(engine);
    }

    /// <summary>
    /// Verifies that a null client factory is rejected.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenClientFactoryIsNull()
    {
        var ex = Assert.Throws<ArgumentNullException>(() =>
            new ImapEngine(
                clientFactory: null!,
                configProvider: new FakeConfigProvider(),
                accountKey: "bewerbung",
                Hash: "ACCOUNT_HASH"));

        Assert.Equal("clientFactory", ex.ParamName);
    }

    /// <summary>
    /// Verifies that a null configuration provider is rejected.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenConfigProviderIsNull()
    {
        var ex = Assert.Throws<ArgumentNullException>(() =>
            new ImapEngine(
                clientFactory: new FakeImapClientFactory(new FakeImapClient('/', new FakeImapFolder("Root", "Root", 0), new FakeImapFolder("Inbox", "Inbox", 0))),
                configProvider: null!,
                accountKey: "bewerbung",
                Hash: "ACCOUNT_HASH"));

        Assert.Equal("configProvider", ex.ParamName);
    }

    /// <summary>
    /// Verifies that a blank account key is rejected.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenAccountKeyIsBlank()
    {
        var ex = Assert.Throws<ArgumentException>(() =>
            new ImapEngine(
                new FakeImapClientFactory(new FakeImapClient('/', new FakeImapFolder("Root", "Root", 0), new FakeImapFolder("Inbox", "Inbox", 0))),
                new FakeConfigProvider(),
                " ",
                "ACCOUNT_HASH"));

        Assert.Equal("accountKey", ex.ParamName);
    }

    /// <summary>
    /// Verifies that missing sent folders throw and still disconnect the client.
    /// </summary>
    [Fact]
    public void GetLastSentMail_ThrowsWhenSentFolderMissing_AndDisconnects()
    {
        var otherFolder = new FakeImapFolder(
            name: "Archive",
            fullName: "Root/Archive",
            count: 3);

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { otherFolder });

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 12);

        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var ex = Assert.Throws<InvalidOperationException>(() => engine.GetLastSentMail());

        Assert.Contains("Gesendete Elemente", ex.Message);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that the newest inbox message is returned with HTML content preferred over plain text.
    /// </summary>
    [Fact]
    public void GetLastInboxMessage_ReturnsNewestMessage()
    {
        var olderUid = new UniqueId(1);
        var newerUid = new UniqueId(2);

        var olderMessage = CreateMessage("old subject", "old text", "<p>old html</p>");
        var newerMessage = CreateMessage("new subject", "new text", "<p>new html</p>");

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 2,
            searchResults: new[] { olderUid, newerUid },
            messages: new Dictionary<UniqueId, MimeMessage>
            {
                [olderUid] = olderMessage,
                [newerUid] = newerMessage
            });

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetLastInboxMessage();

        Assert.Equal(newerUid, result.Uid);
        Assert.Equal("new subject", result.Titel);
        Assert.Equal("<p>new html</p>", result.Context);
        Assert.Equal(FolderAccess.ReadOnly, inbox.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that an empty inbox produces the invalid message DTO.
    /// </summary>
    [Fact]
    public void GetLastInboxMessage_ReturnsInvalid_WhenInboxEmpty()
    {
        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 0,
            searchResults: Array.Empty<UniqueId>());

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetLastInboxMessage();

        Assert.Equal(UniqueId.Invalid, result.Uid);
        Assert.Equal(string.Empty, result.Titel);
        Assert.Equal(string.Empty, result.Context);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that the newest sent message is resolved from the sent folder.
    /// </summary>
    [Fact]
    public void GetLastSentMail_ReturnsNewestMessage()
    {
        var olderUid = new UniqueId(31);
        var newerUid = new UniqueId(32);

        var olderMessage = CreateMessage("older sent subject", "older sent text", "<p>older sent html</p>");
        var newerMessage = CreateMessage("newer sent subject", "newer sent text", "<p>newer sent html</p>");

        var sentFolder = new FakeImapFolder(
            name: "Gesendete Elemente",
            fullName: "Root/Gesendete Elemente",
            count: 2,
            searchResults: new[] { olderUid, newerUid },
            messages: new Dictionary<UniqueId, MimeMessage>
            {
                [olderUid] = olderMessage,
                [newerUid] = newerMessage
            });

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { sentFolder });

        var inbox = new FakeImapFolder("Inbox", "Inbox", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetLastSentMail();

        Assert.Equal(newerUid, result.Uid);
        Assert.Equal("newer sent subject", result.Titel);
        Assert.Equal("<p>newer sent html</p>", result.Context);
        Assert.Equal(FolderAccess.ReadOnly, sentFolder.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that an empty sent folder produces the invalid message DTO.
    /// </summary>
    [Fact]
    public void GetLastSentMail_ReturnsInvalid_WhenSentFolderEmpty()
    {
        var sentFolder = new FakeImapFolder(
            name: "Gesendete Elemente",
            fullName: "Root/Gesendete Elemente",
            count: 0,
            searchResults: Array.Empty<UniqueId>());

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { sentFolder });

        var inbox = new FakeImapFolder("Inbox", "Inbox", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetLastSentMail();

        Assert.Equal(UniqueId.Invalid, result.Uid);
        Assert.Equal(string.Empty, result.Titel);
        Assert.Equal(string.Empty, result.Context);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that all UIDs returned by folder search are exposed unchanged.
    /// </summary>
    [Fact]
    public void GetAllUIDS_ReturnsAllUidsFromFolderSearch()
    {
        var uid1 = new UniqueId(5);
        var uid2 = new UniqueId(9);

        var folder = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 2,
            searchResults: new[] { uid1, uid2 });

        var engine = new ImapEngine(
            new FakeImapClientFactory(new FakeImapClient('/', new FakeImapFolder("Root", "Root", 0), folder)),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetAllUIDS(folder);

        Assert.Equal(new[] { uid1, uid2 }, result);
    }

    /// <summary>
    /// Verifies that inbox UID listing opens the inbox, returns the server order, and disconnects the client.
    /// </summary>
    [Fact]
    public void GetAllUIDInbox_ReturnsInboxUids_AndDisconnects()
    {
        var uid1 = new UniqueId(41);
        var uid2 = new UniqueId(42);

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 2,
            searchResults: new[] { uid1, uid2 });

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetAllUIDInbox();

        Assert.Equal(new[] { uid1, uid2 }, result);
        Assert.Equal(FolderAccess.ReadOnly, inbox.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that sent UID listing resolves the sent folder by full-name suffix and disconnects the client.
    /// </summary>
    [Fact]
    public void GetAllUIDSent_ReturnsSentUids_FromFullNameSuffixMatch()
    {
        var uid1 = new UniqueId(51);
        var uid2 = new UniqueId(52);

        var sentFolder = new FakeImapFolder(
            name: "Archive",
            fullName: "Root.Gesendete Elemente",
            count: 2,
            searchResults: new[] { uid1, uid2 });

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { sentFolder });

        var inbox = new FakeImapFolder("Inbox", "Inbox", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetAllUIDSent();

        Assert.Equal(new[] { uid1, uid2 }, result);
        Assert.Equal(FolderAccess.ReadOnly, sentFolder.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that the inbox folder is opened in read-only mode and returned unchanged.
    /// </summary>
    [Fact]
    public void GetInbox_ReturnsOpenedInboxFolder()
    {
        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 3);

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetInbox(client);

        Assert.Same(inbox, result);
        Assert.Equal(FolderAccess.ReadOnly, inbox.LastOpenAccess);
    }

    /// <summary>
    /// Verifies that the sent folder can be resolved by exact folder name and opened in read-only mode.
    /// </summary>
    [Fact]
    public void GetSent_ReturnsOpenedFolder_WhenNameMatchesExactly()
    {
        var sentFolder = new FakeImapFolder(
            name: "Gesendete Elemente",
            fullName: "Root/Other",
            count: 1);

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { sentFolder });

        var inbox = new FakeImapFolder("Inbox", "Inbox", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetSent(client);

        Assert.Same(sentFolder, result);
        Assert.Equal(FolderAccess.ReadOnly, sentFolder.LastOpenAccess);
    }

    /// <summary>
    /// Verifies that the engine exposes the constructor-supplied account hash unchanged.
    /// </summary>
    [Fact]
    public void GetAccountHash_ReturnsConfiguredHash()
    {
        var expectedHash = "ACCOUNT_HASH_123";
        var engine = new ImapEngine(
            new FakeImapClientFactory(new FakeImapClient('/', new FakeImapFolder("Root", "Root", 0), new FakeImapFolder("Inbox", "Inbox", 0))),
            new FakeConfigProvider(),
            "bewerbung",
            expectedHash);

        var result = engine.getAccountHash();

        Assert.Equal(expectedHash, result);
    }

    /// <summary>
    /// Verifies that folders without messages return no last UID.
    /// </summary>
    [Fact]
    public void GetLastUID_ReturnsNull_WhenFolderContainsNoMessages()
    {
        var folder = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 0,
            searchResults: Array.Empty<UniqueId>());

        var engine = new ImapEngine(
            new FakeImapClientFactory(new FakeImapClient('/', new FakeImapFolder("Root", "Root", 0), folder)),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetLastUID(folder);

        Assert.Null(result);
    }

    /// <summary>
    /// Verifies that the final UID from the search result is returned as the newest message.
    /// </summary>
    [Fact]
    public void GetLastUID_ReturnsLastUid_WhenFolderContainsMessages()
    {
        var uid1 = new UniqueId(12);
        var uid2 = new UniqueId(13);
        var uid3 = new UniqueId(14);

        var folder = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 3,
            searchResults: new[] { uid1, uid2, uid3 });

        var engine = new ImapEngine(
            new FakeImapClientFactory(new FakeImapClient('/', new FakeImapFolder("Root", "Root", 0), folder)),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetLastUID(folder);

        Assert.Equal(uid3, result);
    }

    /// <summary>
    /// Verifies that plain-text content is used when an inbox message has no HTML body.
    /// </summary>
    [Fact]
    public void GetLastInboxMessage_UsesTextBody_WhenHtmlBodyMissing()
    {
        var uid = new UniqueId(21);
        var message = CreateMessage("subject", "plain text body", htmlBody: null);

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 1,
            searchResults: new[] { uid },
            messages: new Dictionary<UniqueId, MimeMessage> { [uid] = message });

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetLastInboxMessage();

        Assert.Equal(uid, result.Uid);
        Assert.Equal("plain text body", result.Context);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that a specific inbox message can be loaded while the client lifecycle is managed by the engine.
    /// </summary>
    [Fact]
    public void GetInboxMessage_ReturnsRequestedMessage_AndDisconnects()
    {
        var uid = new UniqueId(61);
        var message = CreateMessage("Inbox Subject", "Inbox text", "<p>Inbox html</p>");

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 1,
            messages: new Dictionary<UniqueId, MimeMessage> { [uid] = message });

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetInboxMessage(uid);

        Assert.Equal(uid, result.Uid);
        Assert.Equal("Inbox Subject", result.Titel);
        Assert.Equal("<p>Inbox html</p>", result.Context);
        Assert.Equal(FolderAccess.ReadOnly, inbox.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that a specific sent message can be loaded while the client lifecycle is managed by the engine.
    /// </summary>
    [Fact]
    public void GetSentMessage_ReturnsRequestedMessage_AndDisconnects()
    {
        var uid = new UniqueId(71);
        var message = CreateMessage("Sent Subject", "Sent text", "<p>Sent html</p>");

        var sentFolder = new FakeImapFolder(
            name: "Gesendete Elemente",
            fullName: "Root/Gesendete Elemente",
            count: 1,
            messages: new Dictionary<UniqueId, MimeMessage> { [uid] = message });

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { sentFolder });

        var inbox = new FakeImapFolder("Inbox", "Inbox", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung",
            "ACCOUNT_HASH");

        var result = engine.GetSentMessage(uid);

        Assert.Equal(uid, result.Uid);
        Assert.Equal("Sent Subject", result.Titel);
        Assert.Equal("<p>Sent html</p>", result.Context);
        Assert.Equal(FolderAccess.ReadOnly, sentFolder.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that inbox messages are exported to the configured directory.
    /// </summary>
    [Fact]
    public void SaveInboxMail_WritesEmlFileToConfiguredPath()
    {
        var uid = new UniqueId(777);
        var message = CreateMessage("Saved Subject", "Saved text", "<p>Saved html</p>");

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 1,
            messages: new Dictionary<UniqueId, MimeMessage> { [uid] = message });

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);

        var savePath = Path.Combine(Path.GetTempPath(), "MailDirectoryEngineTests", Guid.NewGuid().ToString("N"));
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(savePath),
            "bewerbung",
            "ACCOUNT_HASH");

        try
        {
            var expectedFile = Path.Combine(savePath, $"{uid.Id}.eml");
            var savedFile = engine.SaveInboxMail(uid);

            Assert.Equal(expectedFile, savedFile);
            Assert.True(File.Exists(expectedFile));
            Assert.Contains("Saved Subject", File.ReadAllText(expectedFile));
            Assert.True(client.DisconnectCalled);
        }
        finally
        {
            if (Directory.Exists(savePath))
                Directory.Delete(savePath, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that saving inbox mail fails when no save path is configured and still disconnects the client.
    /// </summary>
    [Fact]
    public void SaveInboxMail_ThrowsWhenSavePathMissing_AndDisconnects()
    {
        var uid = new UniqueId(10);
        var message = CreateMessage("subject", "text", "<p>html</p>");

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 1,
            messages: new Dictionary<UniqueId, MimeMessage> { [uid] = message });

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(savePath: ""),
            "bewerbung",
            "ACCOUNT_HASH");

        var ex = Assert.Throws<InvalidOperationException>(() => engine.SaveInboxMail(uid));

        Assert.Contains("SavePath", ex.Message);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that saving inbox mail fails when the requested UID does not exist and still disconnects the client.
    /// </summary>
    [Fact]
    public void SaveInboxMail_ThrowsWhenUidNotFound_AndDisconnects()
    {
        var existingUid = new UniqueId(22);
        var requestedUid = new UniqueId(99);
        var message = CreateMessage("subject", "text", "<p>html</p>");

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 1,
            messages: new Dictionary<UniqueId, MimeMessage> { [existingUid] = message });

        var root = new FakeImapFolder("Root", "Root", 0);
        var client = new FakeImapClient('/', root, inbox);
        var savePath = Path.Combine(Path.GetTempPath(), "MailDirectoryEngineTests", Guid.NewGuid().ToString("N"));
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(savePath),
            "bewerbung",
            "ACCOUNT_HASH");

        try
        {
            var ex = Assert.Throws<KeyNotFoundException>(() => engine.SaveInboxMail(requestedUid));

            Assert.Contains("UID", ex.Message);
            Assert.True(client.DisconnectCalled);
        }
        finally
        {
            if (Directory.Exists(savePath))
                Directory.Delete(savePath, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that sent messages are exported to the configured directory.
    /// </summary>
    [Fact]
    public void SaveSentMail_WritesEmlFileToConfiguredPath()
    {
        var uid = new UniqueId(888);
        var message = CreateMessage("Saved Sent Subject", "Saved sent text", "<p>Saved sent html</p>");

        var sentFolder = new FakeImapFolder(
            name: "Gesendete Elemente",
            fullName: "Root/Gesendete Elemente",
            count: 1,
            messages: new Dictionary<UniqueId, MimeMessage> { [uid] = message });

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { sentFolder });

        var inbox = new FakeImapFolder("Inbox", "Inbox", 0);
        var client = new FakeImapClient('/', root, inbox);

        var savePath = Path.Combine(Path.GetTempPath(), "MailDirectoryEngineTests", Guid.NewGuid().ToString("N"));
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(savePath),
            "bewerbung",
            "ACCOUNT_HASH");

        try
        {
            var expectedFile = Path.Combine(savePath, $"{uid.Id}.eml");
            var savedFile = engine.SaveSentMail(uid);

            Assert.Equal(expectedFile, savedFile);
            Assert.True(File.Exists(expectedFile));
            Assert.Contains("Saved Sent Subject", File.ReadAllText(expectedFile));
            Assert.True(client.DisconnectCalled);
        }
        finally
        {
            if (Directory.Exists(savePath))
                Directory.Delete(savePath, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that saving sent mail fails when no save path is configured and still disconnects the client.
    /// </summary>
    [Fact]
    public void SaveSentMail_ThrowsWhenSavePathMissing_AndDisconnects()
    {
        var uid = new UniqueId(45);
        var message = CreateMessage("subject", "text", "<p>html</p>");

        var sentFolder = new FakeImapFolder(
            name: "Gesendete Elemente",
            fullName: "Root/Gesendete Elemente",
            count: 1,
            messages: new Dictionary<UniqueId, MimeMessage> { [uid] = message });

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { sentFolder });

        var inbox = new FakeImapFolder("Inbox", "Inbox", 0);
        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(savePath: ""),
            "bewerbung",
            "ACCOUNT_HASH");

        var ex = Assert.Throws<InvalidOperationException>(() => engine.SaveSentMail(uid));

        Assert.Contains("SavePath", ex.Message);
        Assert.True(client.DisconnectCalled);
    }

    /// <summary>
    /// Verifies that saving sent mail fails when the requested UID does not exist and still disconnects the client.
    /// </summary>
    [Fact]
    public void SaveSentMail_ThrowsWhenUidNotFound_AndDisconnects()
    {
        var existingUid = new UniqueId(81);
        var requestedUid = new UniqueId(82);
        var message = CreateMessage("subject", "text", "<p>html</p>");

        var sentFolder = new FakeImapFolder(
            name: "Gesendete Elemente",
            fullName: "Root/Gesendete Elemente",
            count: 1,
            messages: new Dictionary<UniqueId, MimeMessage> { [existingUid] = message });

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { sentFolder });

        var inbox = new FakeImapFolder("Inbox", "Inbox", 0);
        var client = new FakeImapClient('/', root, inbox);
        var savePath = Path.Combine(Path.GetTempPath(), "MailDirectoryEngineTests", Guid.NewGuid().ToString("N"));
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(savePath),
            "bewerbung",
            "ACCOUNT_HASH");

        try
        {
            var ex = Assert.Throws<KeyNotFoundException>(() => engine.SaveSentMail(requestedUid));

            Assert.Contains("UID", ex.Message);
            Assert.True(client.DisconnectCalled);
        }
        finally
        {
            if (Directory.Exists(savePath))
                Directory.Delete(savePath, recursive: true);
        }
    }

    /// <summary>
    /// Creates a MIME message used by the IMAP engine tests.
    /// </summary>
    /// <param name="subject">Subject line for the generated message.</param>
    /// <param name="textBody">Plain-text body content.</param>
    /// <param name="htmlBody">HTML body content.</param>
    /// <returns>Configured MIME message instance.</returns>
    private static MimeMessage CreateMessage(string subject, string? textBody, string? htmlBody)
    {
        var message = new MimeMessage();
        message.From.Add(MailboxAddress.Parse("sender@example.test"));
        message.To.Add(MailboxAddress.Parse("receiver@example.test"));
        message.Subject = subject;

        var bodyBuilder = new BodyBuilder
        {
            TextBody = textBody,
            HtmlBody = htmlBody
        };

        message.Body = bodyBuilder.ToMessageBody();
        return message;
    }
}

internal sealed class FakeImapClientFactory : IImapClientFactory
{
    private readonly IImapClient _client;

    /// <summary>
    /// Initializes the fake factory with the client instance returned for every request.
    /// </summary>
    /// <param name="client">Client instance returned by <see cref="Create(ImapConfig)"/>.</param>
    public FakeImapClientFactory(IImapClient client)
    {
        _client = client;
    }

    /// <summary>
    /// Returns the preconfigured fake client.
    /// </summary>
    /// <param name="config">Ignored IMAP configuration.</param>
    /// <returns>The fake client supplied to the constructor.</returns>
    public IImapClient Create(ImapConfig config)
    {
        return _client;
    }
}

internal sealed class FakeConfigProvider : IImapConfigProvider
{
    private readonly string _savePath;

    /// <summary>
    /// Initializes the fake config provider with a configurable export path.
    /// </summary>
    /// <param name="savePath">Save path returned by <see cref="GetSavePath"/>.</param>
    public FakeConfigProvider(string savePath = @"C:\Temp\mail-export")
    {
        _savePath = savePath;
    }

    /// <summary>
    /// Returns a fixed IMAP configuration for tests.
    /// </summary>
    /// <param name="key">Ignored account key.</param>
    /// <returns>Static configuration values for the fake account.</returns>
    public ImapConfig GetConfig(string key)
    {
        return new ImapConfig
        {
            Host = "example.test",
            Port = 993,
            User = "user",
            Password = "pass"
        };
    }

    /// <summary>
    /// Returns the configured fake save path.
    /// </summary>
    /// <returns>Save path configured for the test double.</returns>
    public string GetSavePath()
    {
        return _savePath;
    }
}

internal sealed class FakeImapClient : IImapClient
{
    private readonly IImapFolder _root;

    /// <summary>
    /// Initializes the fake IMAP client with deterministic folder structure data.
    /// </summary>
    /// <param name="directorySeparator">Directory separator exposed by the fake client.</param>
    /// <param name="root">Root folder returned by <see cref="GetPersonalRoot"/>.</param>
    /// <param name="inbox">Inbox folder returned by <see cref="Inbox"/>.</param>
    public FakeImapClient(char directorySeparator, IImapFolder root, IImapFolder inbox)
    {
        DirectorySeparator = directorySeparator;
        _root = root;
        Inbox = inbox;
    }

    public char DirectorySeparator { get; }
    public IImapFolder Inbox { get; }
    public bool DisconnectCalled { get; private set; }

    /// <summary>
    /// Returns the configured fake personal root folder.
    /// </summary>
    /// <returns>The root folder configured for the test.</returns>
    public IImapFolder GetPersonalRoot()
    {
        return _root;
    }

    /// <summary>
    /// Marks the fake client as disconnected.
    /// </summary>
    /// <param name="quit">Ignored disconnect flag.</param>
    public void Disconnect(bool quit)
    {
        DisconnectCalled = true;
    }

    /// <summary>
    /// Disposes the fake client. No action is required for the test double.
    /// </summary>
    public void Dispose()
    {
    }
}

internal sealed class FakeImapFolder : IImapFolder
{
    private readonly List<IImapFolder> _subfolders;
    private readonly List<UniqueId> _searchResults;
    private readonly Dictionary<UniqueId, MimeMessage> _messages;

    /// <summary>
    /// Initializes a fake folder with predefined search results, messages, and subfolders.
    /// </summary>
    /// <param name="name">Display name of the folder.</param>
    /// <param name="fullName">Full path of the folder.</param>
    /// <param name="count">Message count reported by the folder.</param>
    /// <param name="subfolders">Optional child folders.</param>
    /// <param name="searchResults">Optional search result UIDs.</param>
    /// <param name="messages">Optional message map keyed by UID.</param>
    public FakeImapFolder(
        string name,
        string fullName,
        int count,
        IEnumerable<IImapFolder>? subfolders = null,
        IEnumerable<UniqueId>? searchResults = null,
        IDictionary<UniqueId, MimeMessage>? messages = null)
    {
        Name = name;
        FullName = fullName;
        Count = count;
        _subfolders = subfolders?.ToList() ?? new List<IImapFolder>();
        _searchResults = searchResults?.ToList() ?? new List<UniqueId>();
        _messages = messages != null
            ? new Dictionary<UniqueId, MimeMessage>(messages)
            : new Dictionary<UniqueId, MimeMessage>();
    }

    public string Name { get; }
    public string FullName { get; }
    public int Count { get; }
    public FolderAccess? LastOpenAccess { get; private set; }

    /// <summary>
    /// Records the last access mode used to open the folder.
    /// </summary>
    /// <param name="access">Requested folder access level.</param>
    public void Open(FolderAccess access)
    {
        LastOpenAccess = access;
    }

    /// <summary>
    /// Returns configured child folders, optionally including nested descendants.
    /// </summary>
    /// <param name="recursive">Whether nested subfolders should be included.</param>
    /// <returns>Configured child folders.</returns>
    public IEnumerable<IImapFolder> GetSubfolders(bool recursive)
    {
        if (!recursive)
            return _subfolders;

        var all = new List<IImapFolder>();
        var stack = new Stack<IImapFolder>(_subfolders);

        while (stack.Count > 0)
        {
            var current = stack.Pop();
            all.Add(current);

            if (current is FakeImapFolder fake)
            {
                foreach (var child in fake._subfolders)
                    stack.Push(child);
            }
        }

        return all;
    }

    /// <summary>
    /// Returns the configured search result list.
    /// </summary>
    /// <param name="query">Ignored search query.</param>
    /// <returns>Configured UID search results.</returns>
    public IList<UniqueId> Search(SearchQuery query)
    {
        return _searchResults.ToList();
    }

    /// <summary>
    /// Returns the configured message for the requested UID.
    /// </summary>
    /// <param name="uid">Message identifier to resolve.</param>
    /// <returns>Configured MIME message.</returns>
    /// <exception cref="KeyNotFoundException">
    /// Thrown when no message was configured for the requested UID.
    /// </exception>
    public MimeMessage GetMessage(UniqueId uid)
    {
        if (_messages.TryGetValue(uid, out var message))
            return message;

        throw new KeyNotFoundException($"No message configured for UID {uid}.");
    }
}
