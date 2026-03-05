using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Loads IMAP settings from a JSON file.
    /// </summary>
    internal class ConfigLoader
    {
        /// <summary>
        /// Reads and deserializes the IMAP settings JSON file.
        /// </summary>
        /// <param name="path">Path to the JSON settings file.</param>
        /// <returns>Parsed IMAP settings.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown when the JSON content cannot be deserialized into valid settings.
        /// </exception>
        public static ImapSettings Load(string path)
        {
            var json = File.ReadAllText(path);

            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };

            var settings = JsonSerializer.Deserialize<ImapSettings>(json, options)
                          ?? throw new InvalidOperationException("Invalid IMAP settings JSON.");
            return settings;
        }
    }
}
