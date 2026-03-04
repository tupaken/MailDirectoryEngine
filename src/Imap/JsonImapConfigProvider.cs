using System;

namespace MailDirectoryEngine.src.Imap
{
    internal sealed class JsonImapConfigProvider : IImapConfigProvider
    {
        private readonly string _path;

        public JsonImapConfigProvider(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
                throw new ArgumentException("Config path is required.", nameof(path));

            _path = path;
        }

        public ImapConfig GetConfig(string key)
        {
            if (string.IsNullOrWhiteSpace(key))
                throw new ArgumentException("Account key is required.", nameof(key));

            var settings = ConfigLoader.Load(_path);
            if (!settings.Accounts.TryGetValue(key, out var config))
                throw new ArgumentException($"Unknown account key: '{key}'", nameof(key));

            return config;
        }
    }
}
