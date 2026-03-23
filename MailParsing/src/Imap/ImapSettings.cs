using System.Collections.Generic;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Root settings object for IMAP account configuration.
    /// </summary>
    internal class ImapSettings
    {
        /// <summary>
        /// Gets or sets named IMAP accounts.
        /// </summary>
        public Dictionary<string, ImapConfig> Accounts { get; set; } = new();

        /// <summary>
        /// Gets or sets the default directory path used to persist exported emails.
        /// </summary>
        public string SavePath { get; set; } = "";
    }
}
