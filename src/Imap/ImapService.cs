using System;
using System.Collections.Generic;
using System.Text;
using MailKit.Net.Imap;
using MailKit.Security;

namespace MailDirectoryEngine.src.Imap
{
    internal class ImapService
    {
        public ImapClient CreateClient(ImapConfig config)
        {
            var client = new ImapClient();

            client.Connect(config.Host, config.Port , SecureSocketOptions.SslOnConnect);
            client.Authenticate(config.User, config.Password);
            
            return client;
        }
    }
}
