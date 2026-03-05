using System;
using System.IO;
using MailDirectoryEngine.src.Imap;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class ConfigProviderTests
{
    private static readonly object EnvLock = new();

    [Fact]
    public void JsonImapConfigProvider_ThrowsForUnknownKey()
    {
        var json = """
        {
          "accounts": {
            "test": {
              "host": "imap.example.test",
              "port": 993,
              "user": "user",
              "password": "pass"
            }
          }
        }
        """;

        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, json);
            var provider = new JsonImapConfigProvider(path);

            Assert.Throws<ArgumentException>(() => provider.GetConfig("missing"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void ConfigLoader_LoadsAccountsCaseInsensitive()
    {
        var json = """
        {
          "ACCOUNTS": {
            "sample": {
              "HOST": "mail.example.test",
              "PORT": 995,
              "USER": "user",
              "PASSWORD": "pass"
            }
          }
        }
        """;

        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, json);

            var settings = ConfigLoader.Load(path);

            Assert.True(settings.Accounts.ContainsKey("sample"));
            Assert.Equal("mail.example.test", settings.Accounts["sample"].Host);
            Assert.Equal(995, settings.Accounts["sample"].Port);
            Assert.Equal("user", settings.Accounts["sample"].User);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void JsonImapConfigProvider_GetSavePath_ReturnsConfiguredPath()
    {
        var configuredPath = Path.Combine(Path.GetTempPath(), "mail-export");
        var escapedPath = configuredPath.Replace("\\", "\\\\");
        var json = $$"""
        {
          "accounts": {
            "test": {
              "host": "imap.example.test",
              "port": 993,
              "user": "user",
              "password": "pass"
            }
          },
          "savePath": "{{escapedPath}}"
        }
        """;

        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, json);
            var provider = new JsonImapConfigProvider(path);

            var resolved = provider.GetSavePath();

            Assert.Equal(Path.GetFullPath(configuredPath), resolved);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void JsonImapConfigProvider_GetSavePath_FallsBackToEnvironmentVariable()
    {
        var json = """
        {
          "accounts": {
            "test": {
              "host": "imap.example.test",
              "port": 993,
              "user": "user",
              "password": "pass"
            }
          }
        }
        """;

        lock (EnvLock)
        {
            var original = Environment.GetEnvironmentVariable("MAIL_SAVE_DIR");
            var envPath = Path.Combine(Path.GetTempPath(), "mail-export-from-env");
            var path = Path.GetTempFileName();

            try
            {
                Environment.SetEnvironmentVariable("MAIL_SAVE_DIR", envPath);
                File.WriteAllText(path, json);
                var provider = new JsonImapConfigProvider(path);

                var resolved = provider.GetSavePath();

                Assert.Equal(Path.GetFullPath(envPath), resolved);
            }
            finally
            {
                Environment.SetEnvironmentVariable("MAIL_SAVE_DIR", original);
                File.Delete(path);
            }
        }
    }

    [Fact]
    public void JsonImapConfigProvider_GetSavePath_ThrowsWhenMissingInJsonAndEnv()
    {
        var json = """
        {
          "accounts": {
            "test": {
              "host": "imap.example.test",
              "port": 993,
              "user": "user",
              "password": "pass"
            }
          },
          "savePath": ""
        }
        """;

        lock (EnvLock)
        {
            var original = Environment.GetEnvironmentVariable("MAIL_SAVE_DIR");
            var path = Path.GetTempFileName();

            try
            {
                Environment.SetEnvironmentVariable("MAIL_SAVE_DIR", null);
                File.WriteAllText(path, json);
                var provider = new JsonImapConfigProvider(path);

                var ex = Assert.Throws<InvalidOperationException>(() => provider.GetSavePath());
                Assert.Contains("SavePath", ex.Message);
            }
            finally
            {
                Environment.SetEnvironmentVariable("MAIL_SAVE_DIR", original);
                File.Delete(path);
            }
        }
    }
}
