internal interface IEwsContactClient : IDisposable
{
    Task<ContactPageDto> GetContactsPageAsync(int offset, int pageSize, CancellationToken ct);
}

internal interface IEwsContactClientFactory
{
    IEwsContactClient Create(EwsConfig config);
}

internal interface IEwsConfigProvider
{
    EwsConfig GetConfig(string accountKey);
}
