using System;
using MailDirectoryEngine.src.Imap;
using MailKit;
using MailKit.Net.Imap;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class MailKitImapClientAdapterTests
{
    [Fact]
    public void Constructor_Throws_WhenClientIsNull()
    {
        var ex = Assert.Throws<ArgumentNullException>(() => new MailKitImapClientAdapter(null!));
        Assert.Equal("client", ex.ParamName);
    }

    [Fact]
    public void DirectorySeparator_Throws_WhenNoPersonalNamespacesExist()
    {
        using var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        var ex = Assert.Throws<InvalidOperationException>(() => _ = adapter.DirectorySeparator);

        Assert.Contains("personal namespace", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Inbox_Throws_WhenUnderlyingClientIsNotConnected()
    {
        using var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        Assert.Throws<ServiceNotConnectedException>(() => _ = adapter.Inbox);
    }

    [Fact]
    public void GetPersonalRoot_Throws_WhenNoPersonalNamespacesExist()
    {
        using var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        var ex = Assert.Throws<InvalidOperationException>(() => adapter.GetPersonalRoot());

        Assert.Contains("personal namespace", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Disconnect_DoesNotThrow_WhenUnderlyingClientIsNotConnected()
    {
        using var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        adapter.Disconnect(true);
    }

    [Fact]
    public void Dispose_CanBeCalledMultipleTimes()
    {
        var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        adapter.Dispose();
        adapter.Dispose();
    }
}
