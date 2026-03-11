using System;
using MailDirectoryEngine.src.Imap;
using MailKit;
using MailKit.Net.Imap;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class MailKitImapClientAdapterTests
{
    /// <summary>
    /// Verifies that constructing the adapter with a null client throws.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenClientIsNull()
    {
        var ex = Assert.Throws<ArgumentNullException>(() => new MailKitImapClientAdapter(null!));
        Assert.Equal("client", ex.ParamName);
    }

    /// <summary>
    /// Verifies that reading the directory separator requires a personal namespace.
    /// </summary>
    [Fact]
    public void DirectorySeparator_Throws_WhenNoPersonalNamespacesExist()
    {
        using var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        var ex = Assert.Throws<InvalidOperationException>(() => _ = adapter.DirectorySeparator);

        Assert.Contains("personal namespace", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// Verifies that the inbox property surfaces the underlying connectivity requirement.
    /// </summary>
    [Fact]
    public void Inbox_Throws_WhenUnderlyingClientIsNotConnected()
    {
        using var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        Assert.Throws<ServiceNotConnectedException>(() => _ = adapter.Inbox);
    }

    /// <summary>
    /// Verifies that resolving the personal root requires a personal namespace.
    /// </summary>
    [Fact]
    public void GetPersonalRoot_Throws_WhenNoPersonalNamespacesExist()
    {
        using var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        var ex = Assert.Throws<InvalidOperationException>(() => adapter.GetPersonalRoot());

        Assert.Contains("personal namespace", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// Verifies that disconnect can be called safely on an unconnected client.
    /// </summary>
    [Fact]
    public void Disconnect_DoesNotThrow_WhenUnderlyingClientIsNotConnected()
    {
        using var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        adapter.Disconnect(true);
    }

    /// <summary>
    /// Verifies that disposing the adapter multiple times is safe.
    /// </summary>
    [Fact]
    public void Dispose_CanBeCalledMultipleTimes()
    {
        var client = new ImapClient();
        var adapter = new MailKitImapClientAdapter(client);

        adapter.Dispose();
        adapter.Dispose();
    }
}
