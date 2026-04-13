namespace ContactService.Domain.Abstractions;

internal sealed class EwsConfig
{
    public string ServiceUrl { get; set; } = "";
    public string Mailbox { get; set; } = "";
    public string? Username { get; set; }
    public string? Password { get; set; }
    public string? Domain { get; set; }
    public string? OAuthAccessToken { get; set; }
}
