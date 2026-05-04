using ContactService.Application.Contacts;
using ContactService.Domain.Abstractions;
using ContactService.Domain.Contacts;
using Xunit;

namespace ContactService.Tests.Application.Contacts;

public class ExchangeContactEngineTests
{
    /// <summary>
    /// Verifies that constructor rejects a missing contact client factory.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenFactoryIsNull()
    {
        var configProvider = new FakeEwsConfigProvider();

        var ex = Assert.Throws<ArgumentNullException>(
            () => new ExchangeContactEngine(null!, configProvider, "testaccount"));

        Assert.Equal("factory", ex.ParamName);
    }

    /// <summary>
    /// Verifies that constructor rejects a missing config provider.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenConfigProviderIsNull()
    {
        var factory = new FakeEwsContactClientFactory();

        var ex = Assert.Throws<ArgumentNullException>(
            () => new ExchangeContactEngine(factory, null!, "testaccount"));

        Assert.Equal("configProvider", ex.ParamName);
    }

    /// <summary>
    /// Verifies that constructor rejects an empty account key.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenAccountKeyIsMissing()
    {
        var factory = new FakeEwsContactClientFactory();
        var configProvider = new FakeEwsConfigProvider();

        var ex = Assert.Throws<ArgumentException>(
            () => new ExchangeContactEngine(factory, configProvider, " "));

        Assert.Equal("accountKey", ex.ParamName);
    }

    /// <summary>
    /// Verifies that page size must be a positive integer.
    /// </summary>
    [Fact]
    public async Task GetAllContactsAsync_Throws_WhenPageSizeIsNotPositive()
    {
        var engine = new ExchangeContactEngine(
            new FakeEwsContactClientFactory(),
            new FakeEwsConfigProvider(),
            "testaccount");

        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(
            () => engine.GetAllContactsAsync(0, CancellationToken.None));
    }

    /// <summary>
    /// Verifies that pagination continues until the server does not return a next offset.
    /// </summary>
    [Fact]
    public async Task GetAllContactsAsync_ReadsAllPages_AndAggregatesContacts()
    {
        var factory = new FakeEwsContactClientFactory();
        var configProvider = new FakeEwsConfigProvider();
        factory.Client.Pages.Enqueue(new ContactPageDto(
            Items: new List<ContactDto> { BuildContact("Contact 1") },
            NextOffset: 2));
        factory.Client.Pages.Enqueue(new ContactPageDto(
            Items: new List<ContactDto> { BuildContact("Contact 2"), BuildContact("Contact 3") },
            NextOffset: null));

        var engine = new ExchangeContactEngine(factory, configProvider, "testaccount");

        var contacts = await engine.GetAllContactsAsync(50, CancellationToken.None);

        Assert.Equal(3, contacts.Count);
        Assert.Collection(
            factory.Client.PageRequests,
            request =>
            {
                Assert.Equal(0, request.Offset);
                Assert.Equal(50, request.PageSize);
            },
            request =>
            {
                Assert.Equal(2, request.Offset);
                Assert.Equal(50, request.PageSize);
            });
        Assert.Equal("testaccount", configProvider.ReceivedAccountKey);
        Assert.Same(configProvider.ConfigToReturn, factory.ReceivedConfig);
        Assert.True(factory.Client.Disposed);
    }

    /// <summary>
    /// Verifies that contact creation delegates to the EWS client and disposes it afterwards.
    /// </summary>
    [Fact]
    public async Task AddContactAsync_ForwardsDto_ToClient()
    {
        var factory = new FakeEwsContactClientFactory();
        var configProvider = new FakeEwsConfigProvider();
        var engine = new ExchangeContactEngine(factory, configProvider, "testaccount");
        var dto = BuildContact("New Contact");

        await engine.AddContactAsync(dto, CancellationToken.None);

        Assert.Same(dto, factory.Client.AddedContact);
        Assert.Equal("testaccount", configProvider.ReceivedAccountKey);
        Assert.Same(configProvider.ConfigToReturn, factory.ReceivedConfig);
        Assert.True(factory.Client.Disposed);
    }

    /// <summary>
    /// Verifies that contact creation rejects a missing DTO.
    /// </summary>
    [Fact]
    public async Task AddContactAsync_Throws_WhenDtoIsNull()
    {
        var engine = new ExchangeContactEngine(
            new FakeEwsContactClientFactory(),
            new FakeEwsConfigProvider(),
            "testaccount");

        var ex = await Assert.ThrowsAsync<ArgumentNullException>(
            () => engine.AddContactAsync(null!, CancellationToken.None));

        Assert.Equal("dto", ex.ParamName);
    }

    private static ContactDto BuildContact(string displayName)
    {
        return new ContactDto(
            Id: null,
            DisplayName: displayName,
            GivenName: null,
            MiddleName: null,
            Surname: null,
            Company: null,
            JobTitle: null,
            FileAs: displayName,
            WebPage: null,
            EmailDisplayNames: new Dictionary<string, string>(),
            Emails: new Dictionary<string, string>(),
            ImAddresses: new Dictionary<string, string>(),
            PhoneNumbers: new Dictionary<string, string>(),
            Addresses: new Dictionary<string, ContactAddressDto>(),
            PostalAddressKey: null,
            Email: null,
            BusinessPhone: null,
            HomePhone: null,
            BusinessFax: null,
            MobilePhone: null,
            Notes: null);
    }

    private sealed class FakeEwsConfigProvider : IEwsConfigProvider
    {
        public EwsConfig ConfigToReturn { get; } = new()
        {
            ServiceUrl = "https://ews.example.test/EWS/Exchange.asmx",
            Mailbox = "contact@example.test",
            OAuthAccessToken = "token"
        };

        public string? ReceivedAccountKey { get; private set; }

        public EwsConfig GetConfig(string accountKey)
        {
            ReceivedAccountKey = accountKey;
            return ConfigToReturn;
        }
    }

    private sealed class FakeEwsContactClientFactory : IEwsContactClientFactory
    {
        public FakeEwsContactClient Client { get; } = new();

        public EwsConfig? ReceivedConfig { get; private set; }

        public IEwsContactClient Create(EwsConfig config)
        {
            ReceivedConfig = config;
            return Client;
        }
    }

    private sealed class FakeEwsContactClient : IEwsContactClient
    {
        public Queue<ContactPageDto> Pages { get; } = new();

        public List<(int Offset, int PageSize)> PageRequests { get; } = new();

        public ContactDto? AddedContact { get; private set; }

        public bool Disposed { get; private set; }

        public Task<ContactPageDto> GetContactsPageAsync(int offset, int pageSize, CancellationToken ct)
        {
            PageRequests.Add((offset, pageSize));

            if (Pages.Count == 0)
                throw new InvalidOperationException("No page configured for test.");

            return Task.FromResult(Pages.Dequeue());
        }

        public Task AddContactAsync(ContactDto dto, CancellationToken ct, string? sourceMessageId = null, long? observationId = null)
        {
            AddedContact = dto;
            return Task.CompletedTask;
        }

        public Task<ContactWriteResult> UpsertContactAsync(
            ContactDto dto,
            CancellationToken ct,
            string? sourceMessageId = null,
            long? observationId = null)
        {
            AddedContact = dto;
            return Task.FromResult(new ContactWriteResult("created", "ews-1"));
        }

        public void Dispose()
        {
            Disposed = true;
        }
    }
}
