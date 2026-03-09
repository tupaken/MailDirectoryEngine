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
    [Fact]
    public void DefaultConstructor_CreatesInstance()
    {
        var engine = new ImapEngine();
        Assert.NotNull(engine);
    }

    [Fact]
    public void Constructor_Throws_WhenClientFactoryIsNull()
    {
        var ex = Assert.Throws<ArgumentNullException>(() =>
            new ImapEngine(
                clientFactory: null!,
                configProvider: new FakeConfigProvider(),
                accountKey: "bewerbung"));

        Assert.Equal("clientFactory", ex.ParamName);
    }

    [Fact]
    public void Constructor_Throws_WhenConfigProviderIsNull()
    {
        var ex = Assert.Throws<ArgumentNullException>(() =>
            new ImapEngine(
                clientFactory: new FakeImapClientFactory(new FakeImapClient('/', new FakeImapFolder("Root", "Root", 0), new FakeImapFolder("Inbox", "Inbox", 0))),
                configProvider: null!,
                accountKey: "bewerbung"));

        Assert.Equal("configProvider", ex.ParamName);
    }

    [Fact]
    public void Constructor_Throws_WhenAccountKeyIsBlank()
    {
        var ex = Assert.Throws<ArgumentException>(() =>
            new ImapEngine(
                new FakeImapClientFactory(new FakeImapClient('/', new FakeImapFolder("Root", "Root", 0), new FakeImapFolder("Inbox", "Inbox", 0))),
                new FakeConfigProvider(),
                " "));

        Assert.Equal("accountKey", ex.ParamName);
    }

    [Fact]
    public void GetSendCount_UsesSentFolderCount()
    {
        var sentFolder = new FakeImapFolder(
            name: "Gesendete Elemente",
            fullName: "Root/Gesendete Elemente",
            count: 7);

        var otherFolder = new FakeImapFolder(
            name: "Other",
            fullName: "Root/Other",
            count: 3);

        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0,
            subfolders: new[] { otherFolder, sentFolder });

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 12);

        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung");

        var count = engine.GetSendCount();

        Assert.Equal(7, count);
        Assert.Equal(FolderAccess.ReadOnly, sentFolder.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

    [Fact]
    public void GetInboxCount_UsesInboxCount()
    {
        var root = new FakeImapFolder(
            name: "Root",
            fullName: "Root",
            count: 0);

        var inbox = new FakeImapFolder(
            name: "Inbox",
            fullName: "Inbox",
            count: 42);

        var client = new FakeImapClient('/', root, inbox);
        var engine = new ImapEngine(
            new FakeImapClientFactory(client),
            new FakeConfigProvider(),
            "bewerbung");

        var count = engine.GetInboxCount();

        Assert.Equal(42, count);
        Assert.Equal(FolderAccess.ReadOnly, inbox.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

    [Fact]
    public void GetSendCount_ThrowsWhenSentFolderMissing_AndDisconnects()
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
            "bewerbung");

        var ex = Assert.Throws<InvalidOperationException>(() => engine.GetSendCount());

        Assert.Contains("Gesendete Elemente", ex.Message);
        Assert.True(client.DisconnectCalled);
    }

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
            "bewerbung");

        var result = engine.GetLastInboxMessage();

        Assert.NotNull(result);
        Assert.Equal(newerUid, result!.Uid);
        Assert.Equal("new subject", result.Titel);
        Assert.Equal("<p>new html</p>", result.Context);
        Assert.Equal(FolderAccess.ReadOnly, inbox.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

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
            "bewerbung");

        var result = engine.GetLastInboxMessage();

        Assert.NotNull(result);
        Assert.Equal(UniqueId.Invalid, result!.Uid);
        Assert.Equal(string.Empty, result.Titel);
        Assert.Equal(string.Empty, result.Context);
        Assert.True(client.DisconnectCalled);
    }

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
            "bewerbung");

        var result = engine.GetLastSentMail();

        Assert.NotNull(result);
        Assert.Equal(newerUid, result!.Uid);
        Assert.Equal("newer sent subject", result.Titel);
        Assert.Equal("<p>newer sent html</p>", result.Context);
        Assert.Equal(FolderAccess.ReadOnly, sentFolder.LastOpenAccess);
        Assert.True(client.DisconnectCalled);
    }

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
            "bewerbung");

        var result = engine.GetLastSentMail();

        Assert.NotNull(result);
        Assert.Equal(UniqueId.Invalid, result!.Uid);
        Assert.Equal(string.Empty, result.Titel);
        Assert.Equal(string.Empty, result.Context);
        Assert.True(client.DisconnectCalled);
    }

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
            "bewerbung");

        var result = engine.GetAllUIDS(folder);

        Assert.Equal(new[] { uid1, uid2 }, result);
    }

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
            "bewerbung");

        var result = engine.GetLastUID(folder);

        Assert.Null(result);
    }

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
            "bewerbung");

        var result = engine.GetLastUID(folder);

        Assert.Equal(uid3, result);
    }

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
            "bewerbung");

        try
        {
            engine.SaveInboxMail(uid);

            var expectedFile = Path.Combine(savePath, $"{uid.Id}.eml");
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
            "bewerbung");

        var ex = Assert.Throws<InvalidOperationException>(() => engine.SaveInboxMail(uid));

        Assert.Contains("SavePath", ex.Message);
        Assert.True(client.DisconnectCalled);
    }

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
            "bewerbung");

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
            "bewerbung");

        try
        {
            engine.SaveSentMail(uid);

            var expectedFile = Path.Combine(savePath, $"{uid.Id}.eml");
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
            "bewerbung");

        var ex = Assert.Throws<InvalidOperationException>(() => engine.SaveSentMail(uid));

        Assert.Contains("SavePath", ex.Message);
        Assert.True(client.DisconnectCalled);
    }

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
            "bewerbung");

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

    private static MimeMessage CreateMessage(string subject, string textBody, string htmlBody)
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

    public FakeImapClientFactory(IImapClient client)
    {
        _client = client;
    }

    public IImapClient Create(ImapConfig config)
    {
        return _client;
    }
}

internal sealed class FakeConfigProvider : IImapConfigProvider
{
    private readonly string _savePath;

    public FakeConfigProvider(string savePath = @"C:\Temp\mail-export")
    {
        _savePath = savePath;
    }

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

    public string GetSavePath()
    {
        return _savePath;
    }
}

internal sealed class FakeImapClient : IImapClient
{
    private readonly IImapFolder _root;

    public FakeImapClient(char directorySeparator, IImapFolder root, IImapFolder inbox)
    {
        DirectorySeparator = directorySeparator;
        _root = root;
        Inbox = inbox;
    }

    public char DirectorySeparator { get; }
    public IImapFolder Inbox { get; }
    public bool DisconnectCalled { get; private set; }

    public IImapFolder GetPersonalRoot()
    {
        return _root;
    }

    public void Disconnect(bool quit)
    {
        DisconnectCalled = true;
    }

    public void Dispose()
    {
    }
}

internal sealed class FakeImapFolder : IImapFolder
{
    private readonly List<IImapFolder> _subfolders;
    private readonly List<UniqueId> _searchResults;
    private readonly Dictionary<UniqueId, MimeMessage> _messages;

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

    public void Open(FolderAccess access)
    {
        LastOpenAccess = access;
    }

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

    public IList<UniqueId> Search(SearchQuery query)
    {
        return _searchResults.ToList();
    }

    public MimeMessage GetMessage(UniqueId uid)
    {
        if (_messages.TryGetValue(uid, out var message))
            return message;

        throw new KeyNotFoundException($"No message configured for UID {uid}.");
    }
}
