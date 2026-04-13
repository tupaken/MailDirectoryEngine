using ContactService.Infrastructure.Ews;
using Xunit;

namespace ContactService.Tests.Infrastructure.Ews;

public class EnvEwsConfigProviderTests
{
    /// <summary>
    /// Verifies that OAuth configuration is resolved from environment variables.
    /// </summary>
    [Fact]
    public void GetConfig_ReturnsOAuthConfiguration()
    {
        var accountKey = $"test{Guid.NewGuid():N}";
        var prefix = BuildPrefix(accountKey);
        var keys = new[]
        {
            prefix + "SERVICE_URL",
            prefix + "MAILBOX",
            prefix + "AUTH_MODE",
            prefix + "OAUTH_ACCESS_TOKEN"
        };
        var snapshot = CaptureEnvironment(keys);

        try
        {
            Environment.SetEnvironmentVariable(prefix + "SERVICE_URL", "https://ews.example.test/EWS/Exchange.asmx");
            Environment.SetEnvironmentVariable(prefix + "MAILBOX", "contact@example.test");
            Environment.SetEnvironmentVariable(prefix + "AUTH_MODE", "oauth");
            Environment.SetEnvironmentVariable(prefix + "OAUTH_ACCESS_TOKEN", "token-123");

            var provider = new EnvEwsConfigProvider();
            var config = provider.GetConfig(accountKey);

            Assert.Equal("https://ews.example.test/EWS/Exchange.asmx", config.ServiceUrl);
            Assert.Equal("contact@example.test", config.Mailbox);
            Assert.Equal("token-123", config.OAuthAccessToken);
            Assert.Null(config.Username);
            Assert.Null(config.Password);
        }
        finally
        {
            RestoreEnvironment(snapshot);
        }
    }

    /// <summary>
    /// Verifies that basic-auth configuration uses mailbox as username when no explicit username is provided.
    /// </summary>
    [Fact]
    public void GetConfig_ReturnsBasicConfiguration_WithMailboxFallbackUsername()
    {
        var accountKey = $"test{Guid.NewGuid():N}";
        var prefix = BuildPrefix(accountKey);
        var keys = new[]
        {
            prefix + "SERVICE_URL",
            prefix + "MAILBOX",
            prefix + "AUTH_MODE",
            prefix + "PASSWORD",
            prefix + "DOMAIN",
            prefix + "USERNAME"
        };
        var snapshot = CaptureEnvironment(keys);

        try
        {
            Environment.SetEnvironmentVariable(prefix + "SERVICE_URL", "https://ews.example.test/EWS/Exchange.asmx");
            Environment.SetEnvironmentVariable(prefix + "MAILBOX", "contact@example.test");
            Environment.SetEnvironmentVariable(prefix + "AUTH_MODE", "basic");
            Environment.SetEnvironmentVariable(prefix + "PASSWORD", "super-secret");
            Environment.SetEnvironmentVariable(prefix + "DOMAIN", "EXAMPLE");
            Environment.SetEnvironmentVariable(prefix + "USERNAME", null);

            var provider = new EnvEwsConfigProvider();
            var config = provider.GetConfig(accountKey);

            Assert.Equal("https://ews.example.test/EWS/Exchange.asmx", config.ServiceUrl);
            Assert.Equal("contact@example.test", config.Mailbox);
            Assert.Equal("contact@example.test", config.Username);
            Assert.Equal("super-secret", config.Password);
            Assert.Equal("EXAMPLE", config.Domain);
            Assert.Null(config.OAuthAccessToken);
        }
        finally
        {
            RestoreEnvironment(snapshot);
        }
    }

    /// <summary>
    /// Verifies that unsupported auth modes are rejected.
    /// </summary>
    [Fact]
    public void GetConfig_Throws_WhenAuthModeIsUnsupported()
    {
        var accountKey = $"test{Guid.NewGuid():N}";
        var prefix = BuildPrefix(accountKey);
        var keys = new[]
        {
            prefix + "SERVICE_URL",
            prefix + "MAILBOX",
            prefix + "AUTH_MODE"
        };
        var snapshot = CaptureEnvironment(keys);

        try
        {
            Environment.SetEnvironmentVariable(prefix + "SERVICE_URL", "https://ews.example.test/EWS/Exchange.asmx");
            Environment.SetEnvironmentVariable(prefix + "MAILBOX", "contact@example.test");
            Environment.SetEnvironmentVariable(prefix + "AUTH_MODE", "kerberos");

            var provider = new EnvEwsConfigProvider();
            var ex = Assert.Throws<InvalidOperationException>(() => provider.GetConfig(accountKey));

            Assert.Contains("Unsupported auth mode", ex.Message, StringComparison.Ordinal);
        }
        finally
        {
            RestoreEnvironment(snapshot);
        }
    }

    /// <summary>
    /// Verifies that required variables produce clear errors when missing.
    /// </summary>
    [Fact]
    public void GetConfig_Throws_WhenRequiredVariableIsMissing()
    {
        var accountKey = $"test{Guid.NewGuid():N}";
        var prefix = BuildPrefix(accountKey);
        var keys = new[]
        {
            prefix + "SERVICE_URL",
            prefix + "MAILBOX",
            prefix + "AUTH_MODE",
            prefix + "OAUTH_ACCESS_TOKEN"
        };
        var snapshot = CaptureEnvironment(keys);

        try
        {
            Environment.SetEnvironmentVariable(prefix + "SERVICE_URL", null);
            Environment.SetEnvironmentVariable(prefix + "MAILBOX", "contact@example.test");
            Environment.SetEnvironmentVariable(prefix + "AUTH_MODE", "oauth");
            Environment.SetEnvironmentVariable(prefix + "OAUTH_ACCESS_TOKEN", "token-123");

            var provider = new EnvEwsConfigProvider();
            var ex = Assert.Throws<InvalidOperationException>(() => provider.GetConfig(accountKey));

            Assert.Contains(prefix + "SERVICE_URL", ex.Message, StringComparison.Ordinal);
        }
        finally
        {
            RestoreEnvironment(snapshot);
        }
    }

    private static string BuildPrefix(string accountKey)
    {
        return $"EWS__{accountKey.ToUpperInvariant()}__";
    }

    private static Dictionary<string, string?> CaptureEnvironment(IEnumerable<string> keys)
    {
        var snapshot = new Dictionary<string, string?>(StringComparer.Ordinal);
        foreach (var key in keys)
            snapshot[key] = Environment.GetEnvironmentVariable(key);

        return snapshot;
    }

    private static void RestoreEnvironment(Dictionary<string, string?> snapshot)
    {
        foreach (var pair in snapshot)
            Environment.SetEnvironmentVariable(pair.Key, pair.Value);
    }
}
