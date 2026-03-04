using System;
using System.Collections.Generic;
using System.Text;

namespace MailDirectoryEngine.src.Imap
{
    public class ImapConfig
    {
        public string Host { get; set; } = "";
        public int Port { get; set; } = 993;
        public string User { get; set; } = "";
        public string Password { get; set; } = "";
    }
}
