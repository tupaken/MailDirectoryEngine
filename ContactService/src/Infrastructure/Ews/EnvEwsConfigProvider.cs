using ContactService.Domain.Abstractions;
using DotNetEnv;

namespace ContactService.Infrastructure.Ews;

internal sealed class EnvEwsConfigProvider : IEwsConfigProvider
{
    /// <summary>
    /// Loads repository-level <c>.env</c> file when present.
    /// </summary>
    public EnvEwsConfigProvider()
    {
        var envPath = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".env"));
        if (File.Exists(envPath))
            Env.Load(envPath);
    }

    /// <summary>
    /// Resolves account-specific EWS settings from environment variables.
    /// </summary>
    /// <param name="accountKey">Logical account key (for example <c>bewerbung</c>).</param>
    /// <returns>Resolved EWS configuration for the requested account.</returns>
    public EwsConfig GetConfig(string accountKey)
    {
        if (string.IsNullOrWhiteSpace(accountKey))
            throw new ArgumentException("Account key is required.", nameof(accountKey));

        var prefix = $"EWS__{accountKey.ToUpperInvariant()}__";

        static string Req(string name, string prefix) =>
            Environment.GetEnvironmentVariable(prefix + name)
            ?? throw new InvalidOperationException($"Missing env var: {prefix}{name}");

        var authMode = (Environment.GetEnvironmentVariable(prefix + "AUTH_MODE") ?? "oauth").ToLowerInvariant();

        var config = new EwsConfig
        {
            ServiceUrl = Req("SERVICE_URL", prefix),
            Mailbox = Req("MAILBOX", prefix)
        };

        if (authMode == "oauth")
        {
            config.OAuthAccessToken = Req("OAUTH_ACCESS_TOKEN", prefix);
        }
        else if (authMode == "basic")
        {
            config.Username = Environment.GetEnvironmentVariable(prefix + "USERNAME") ?? config.Mailbox;
            config.Password = Req("PASSWORD", prefix);
            config.Domain = Environment.GetEnvironmentVariable(prefix + "DOMAIN");
        }
        else
        {
            throw new InvalidOperationException($"Unsupported auth mode: {authMode}");
        }

        return config;
    }
}
