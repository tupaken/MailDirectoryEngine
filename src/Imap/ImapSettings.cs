using System;
using System.Collections.Generic;
using System.Text;

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
    
        public string SavePath { get; set; } = "";
    }
}
