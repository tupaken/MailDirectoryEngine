using ContactService.Domain.Abstractions;
using ContactService.Domain.Contacts;

namespace ContactService.Application.Contacts;

internal sealed class ExchangeContactEngine
{
    private readonly IEwsContactClientFactory _factory;
    private readonly IEwsConfigProvider _configProvider;
    private readonly string _accountKey;

    public ExchangeContactEngine(
        IEwsContactClientFactory factory,
        IEwsConfigProvider configProvider,
        string accountKey)
    {
        _factory = factory ?? throw new ArgumentNullException(nameof(factory));
        _configProvider = configProvider ?? throw new ArgumentNullException(nameof(configProvider));
        if (string.IsNullOrWhiteSpace(accountKey))
            throw new ArgumentException("Account key is required.", nameof(accountKey));

        _accountKey = accountKey;
    }

    /// <summary>
    /// Reads all contacts from Exchange by repeatedly loading pages until no next offset exists.
    /// </summary>
    /// <param name="pageSize">Maximum page size per EWS request.</param>
    /// <param name="ct">Cancellation token for the operation.</param>
    /// <returns>Aggregated contact list across all EWS pages.</returns>
    public async Task<IReadOnlyList<ContactDto>> GetAllContactsAsync(int pageSize, CancellationToken ct)
    {
        if (pageSize <= 0)
            throw new ArgumentOutOfRangeException(nameof(pageSize));

        var config = _configProvider.GetConfig(_accountKey);
        using var client = _factory.Create(config);

        var all = new List<ContactDto>();
        var offset = 0;

        while (true)
        {
            ct.ThrowIfCancellationRequested();
            var page = await client.GetContactsPageAsync(offset, pageSize, ct).ConfigureAwait(false);

            all.AddRange(page.Items);
            if (page.NextOffset is null)
                break;

            offset = page.NextOffset.Value;
        }

        return all;
    }

    /// <summary>
    /// Creates a new contact in Exchange for the configured account.
    /// </summary>
    /// <param name="dto">Contact data to create.</param>
    /// <param name="ct">Cancellation token for the operation.</param>
    public async Task AddContactAsync(ContactDto dto, CancellationToken ct)
    {
        if (dto is null)
            throw new ArgumentNullException(nameof(dto));

        var config = _configProvider.GetConfig(_accountKey);
        using var client = _factory.Create(config);

        await client.AddContactAsync(dto, ct).ConfigureAwait(false);
    }

}
