using System;
using System.IO;
using MailDirectoryEngine.src.Imap;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class ConfigProviderTests
{
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
}
