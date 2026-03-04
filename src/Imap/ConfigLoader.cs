using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace MailDirectoryEngine.src.Imap
{
    internal class ConfigLoader
    {
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
