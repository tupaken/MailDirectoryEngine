using System;
using System.Collections.Generic;
using System.Text;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Represents IMAP connection settings for a single account.
    /// </summary>
    public class ImapConfig
    {
        /// <summary>
        /// Gets or sets the IMAP server host name.
        /// </summary>
        public string Host { get; set; } = "";

        /// <summary>
        /// Gets or sets the IMAP server port.
        /// </summary>
        public int Port { get; set; } = 993;

        /// <summary>
        /// Gets or sets the account user name.
        /// </summary>
        public string User { get; set; } = "";

        /// <summary>
        /// Gets or sets the account password.
        /// </summary>
        public string Password { get; set; } = "";
    }
}
