using System;
using MailDirectoryEngine.src.Imap;
using MailKit.Net.Imap;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class ImapServiceTests
{
    [Fact]
    public void DefaultConstructor_CreatesInstance()
    {
        var service = new ImapService();
        Assert.NotNull(service);
    }

    [Fact]
    public void Constructor_Throws_WhenClientFactoryIsNull()
    {
        var ex = Assert.Throws<ArgumentNullException>(() => new ImapService(clientFactory: null!));
        Assert.Equal("clientFactory", ex.ParamName);
    }

    [Fact]
    public void Create_Throws_WhenConfigIsNull()
    {
        var service = new TestableImapService(throwOnConnect: false);
        var ex = Assert.Throws<ArgumentNullException>(() => service.Create(null!));
        Assert.Equal("config", ex.ParamName);
    }

    [Fact]
    public void Create_CallsConnectAndAuthenticate_WithConfig()
    {
        var config = new ImapConfig
        {
            Host = "imap.example.test",
            Port = 993,
            User = "user@example.test",
            Password = "secret"
        };

        var service = new TestableImapService(throwOnConnect: false);

        var client = service.Create(config);

        Assert.NotNull(client);
        Assert.True(service.ConnectAndAuthenticateCalled);
        Assert.Same(config, service.ReceivedConfig);
    }

    [Fact]
    public void Create_WrapsAuthException_InInvalidOperationException()
    {
        var config = new ImapConfig
        {
            Host = "imap.example.test",
            Port = 993,
            User = "user@example.test",
            Password = "wrong"
        };

        var service = new TestableImapService(throwOnConnect: true);

        var ex = Assert.Throws<InvalidOperationException>(() => service.Create(config));

        Assert.Contains("connect/auth", ex.Message, StringComparison.OrdinalIgnoreCase);
        Assert.NotNull(ex.InnerException);
        Assert.Equal("Simulated auth failure", ex.InnerException!.Message);
    }

    [Fact]
    public void ConnectAndAuthenticate_CanBeOverridden()
    {
        var config = new ImapConfig
        {
            Host = "imap.example.test",
            Port = 993,
            User = "override@example.test",
            Password = "secret"
        };

        var service = new TestableImapService(throwOnConnect: false);

        service.Create(config);

        Assert.True(service.ConnectAndAuthenticateCalled);
        Assert.Same(config, service.ReceivedConfig);
    }
}

internal sealed class TestableImapService : ImapService
{
    private readonly bool _throwOnConnect;

    public TestableImapService(bool throwOnConnect)
        : base(() => new ImapClient())
    {
        _throwOnConnect = throwOnConnect;
    }

    public bool ConnectAndAuthenticateCalled { get; private set; }
    public ImapConfig? ReceivedConfig { get; private set; }

    internal override void ConnectAndAuthenticate(ImapClient client, ImapConfig config)
    {
        ConnectAndAuthenticateCalled = true;
        ReceivedConfig = config;

        if (_throwOnConnect)
            throw new InvalidOperationException("Simulated auth failure");
    }
}
