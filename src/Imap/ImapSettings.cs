using System;
using System.Collections.Generic;
using System.Text;

namespace MailDirectoryEngine.src.Imap
{
    internal class ImapSettings
    {
        public Dictionary<string, ImapConfig> Accounts { get; set; } = new();
    }
}
