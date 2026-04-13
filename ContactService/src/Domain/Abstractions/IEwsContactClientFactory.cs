namespace ContactService.Domain.Abstractions;

internal interface IEwsContactClientFactory
{
    IEwsContactClient Create(EwsConfig config);
}
