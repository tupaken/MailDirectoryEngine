namespace ContactService.Domain.Abstractions;

internal interface IEwsConfigProvider
{
    EwsConfig GetConfig(string accountKey);
}
