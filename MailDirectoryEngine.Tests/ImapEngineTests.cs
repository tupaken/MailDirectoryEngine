using System.Collections.Generic;
using System.Linq;
using System;
using MailDirectoryEngine.src.Imap;
using MailKit;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class ImapEngineTests
{
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

    public FakeImapFolder(string name, string fullName, int count, IEnumerable<IImapFolder>? subfolders = null)
    {
        Name = name;
        FullName = fullName;
        Count = count;
        _subfolders = subfolders?.ToList() ?? new List<IImapFolder>();
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
}
