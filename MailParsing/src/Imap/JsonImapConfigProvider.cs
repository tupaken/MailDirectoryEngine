using System;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Loads IMAP account configuration from a JSON file.
    /// </summary>
    internal sealed class JsonImapConfigProvider : IImapConfigProvider
    {
        private readonly string _path;

        /// <summary>
        /// Initializes a new provider for the given JSON file path.
        /// </summary>
        /// <param name="path">Path to the IMAP configuration JSON file.</param>
        public JsonImapConfigProvider(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
                throw new ArgumentException("Config path is required.", nameof(path));

            _path = path;
        }

        /// <summary>
        /// Returns IMAP settings for the requested account key.
        /// </summary>
        /// <param name="key">Account key in the configuration file.</param>
        /// <returns>The account configuration.</returns>
        /// <exception cref="ArgumentException">
        /// Thrown when the key is empty or the account does not exist.
        /// </exception>
        public ImapConfig GetConfig(string key)
        {
            if (string.IsNullOrWhiteSpace(key))
                throw new ArgumentException("Account key is required.", nameof(key));

            var settings = ConfigLoader.Load(_path);
            var accounts = settings.Accounts
                ?? throw new InvalidOperationException("IMAP settings are missing the 'accounts' section.");
            if (accounts.Count == 0)
                throw new InvalidOperationException("IMAP settings do not contain any configured accounts.");

            if (!accounts.TryGetValue(key, out var config))
                throw new ArgumentException($"Unknown account key: '{key}'", nameof(key));

            return config;
        }

        /// <summary>
        /// Resolves the email export directory from JSON settings or MAIL_SAVE_DIR environment variable.
        /// </summary>
        /// <returns>Normalized full path to the export directory.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown when neither JSON SavePath nor MAIL_SAVE_DIR is set.
        /// </exception>
        public string GetSavePath()
        {
            var settings = ConfigLoader.Load(_path);

            var rawPath = string.IsNullOrWhiteSpace(settings.SavePath)
                ? Environment.GetEnvironmentVariable("MAIL_SAVE_DIR")
                : settings.SavePath;

            if (string.IsNullOrWhiteSpace(rawPath))
                throw new InvalidOperationException("SavePath is missing (JSON or ENV MAIL_SAVE_DIR).");

            var expanded = Environment.ExpandEnvironmentVariables(rawPath);
            return Path.GetFullPath(expanded);
        }
    }
}
