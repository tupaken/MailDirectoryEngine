using System;
using System.Collections.Generic;
using System.Globalization;

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

            if (TryGetConfigFromEnvironment(key, out var envConfig))
                return envConfig;

            if (!File.Exists(_path))
                throw new InvalidOperationException(
                    $"IMAP settings file was not found at '{_path}'. " +
                    $"Either provide the file or set IMAP__{key.ToUpperInvariant()}__HOST/PORT/USER/PASSWORD.");

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
            var envPath = GetFirstEnvironmentValue("MAIL_SAVE_DIR", "IMAP_SAVE_PATH");

            if (!string.IsNullOrWhiteSpace(envPath))
            {
                var expandedFromEnv = Environment.ExpandEnvironmentVariables(envPath);
                return Path.GetFullPath(expandedFromEnv);
            }

            if (!File.Exists(_path))
                throw new InvalidOperationException(
                    $"SavePath is missing. Set MAIL_SAVE_DIR (or IMAP_SAVE_PATH) or provide '{_path}'.");

            var settings = ConfigLoader.Load(_path);

            var rawPath = settings.SavePath;

            if (string.IsNullOrWhiteSpace(rawPath))
                throw new InvalidOperationException("SavePath is missing (JSON or ENV MAIL_SAVE_DIR).");

            var expanded = Environment.ExpandEnvironmentVariables(rawPath);
            return Path.GetFullPath(expanded);
        }

        private static bool TryGetConfigFromEnvironment(string key, out ImapConfig config)
        {
            config = null!;

            var accountKey = key.Trim().ToUpperInvariant();
            var host = GetFirstEnvironmentValue($"IMAP__{accountKey}__HOST");
            var portText = GetFirstEnvironmentValue($"IMAP__{accountKey}__PORT");
            var user = GetFirstEnvironmentValue($"IMAP__{accountKey}__USER");
            var password = GetFirstEnvironmentValue($"IMAP__{accountKey}__PASSWORD");

            if (string.IsNullOrWhiteSpace(host) &&
                string.IsNullOrWhiteSpace(portText) &&
                string.IsNullOrWhiteSpace(user) &&
                string.IsNullOrWhiteSpace(password))
            {
                return false;
            }

            var missing = new List<string>();
            if (string.IsNullOrWhiteSpace(host)) missing.Add("HOST");
            if (string.IsNullOrWhiteSpace(portText)) missing.Add("PORT");
            if (string.IsNullOrWhiteSpace(user)) missing.Add("USER");
            if (string.IsNullOrWhiteSpace(password)) missing.Add("PASSWORD");

            if (missing.Count > 0)
            {
                throw new InvalidOperationException(
                    $"Incomplete IMAP environment configuration for '{key}'. Missing: {string.Join(", ", missing)}. " +
                    $"Expected IMAP__{accountKey}__HOST/PORT/USER/PASSWORD.");
            }

            if (!int.TryParse(portText, NumberStyles.Integer, CultureInfo.InvariantCulture, out var port) || port <= 0)
                throw new InvalidOperationException(
                    $"Invalid IMAP port '{portText}' for account '{key}'. Expected a positive integer.");

            config = new ImapConfig
            {
                Host = host!,
                Port = port,
                User = user!,
                Password = password!
            };
            return true;
        }

        private static string? GetFirstEnvironmentValue(params string[] names)
        {
            foreach (var name in names)
            {
                var value = Environment.GetEnvironmentVariable(name);
                if (!string.IsNullOrWhiteSpace(value))
                    return value;
            }

            return null;
        }
    }
}
