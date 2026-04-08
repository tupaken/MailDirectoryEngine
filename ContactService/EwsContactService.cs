using Microsoft.Exchange.WebServices.Data;
using System.Text;

internal sealed class EwsContactService : IEwsContactClientFactory
{
    public IEwsContactClient Create(EwsConfig config)
    {
        if (config is null)
            throw new ArgumentNullException(nameof(config));
        if (string.IsNullOrWhiteSpace(config.ServiceUrl))
            throw new ArgumentException("ServiceUrl is required.", nameof(config));
        if (string.IsNullOrWhiteSpace(config.Mailbox))
            throw new ArgumentException("Mailbox is required.", nameof(config));

        try
        {
            var service = new ExchangeService(ExchangeVersion.Exchange2013_SP1)
            {
                Url = new Uri(config.ServiceUrl)
            };

            if (!string.IsNullOrWhiteSpace(config.OAuthAccessToken))
            {
                service.Credentials = new OAuthCredentials(config.OAuthAccessToken);
                service.HttpHeaders["X-AnchorMailbox"] = config.Mailbox;
            }
            else if (!string.IsNullOrWhiteSpace(config.Username) && !string.IsNullOrWhiteSpace(config.Password))
            {
                service.Credentials = new WebCredentials(config.Username, config.Password, config.Domain);
                service.PreAuthenticate = true;
                service.HttpHeaders["Authorization"] =
                    BuildBasicAuthorizationHeader(config.Username, config.Password);
                service.HttpHeaders["X-AnchorMailbox"] = config.Mailbox;
            }
            else
            {
                throw new InvalidOperationException("No valid EWS auth configuration found.");
            }

            return new EwsContactClientAdapter(service);
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException($"EWS client creation failed for mailbox '{config.Mailbox}'.", ex);
        }
    }

    private static string BuildBasicAuthorizationHeader(string username, string password)
    {
        var raw = $"{username}:{password}";
        var encoded = Convert.ToBase64String(Encoding.UTF8.GetBytes(raw));
        return $"Basic {encoded}";
    }
}
