using System;
using MailKit.Net.Imap;

namespace MailDirectoryEngine.src.Imap
{
    internal sealed class MailKitImapClientAdapter : IImapClient
    {
        private readonly ImapClient _client;

        public MailKitImapClientAdapter(ImapClient client)
        {
            _client = client ?? throw new ArgumentNullException(nameof(client));
        }

        public char DirectorySeparator
        {
            get
            {
                if (_client.PersonalNamespaces.Count == 0)
                    throw new InvalidOperationException("No personal namespaces available.");

                return _client.PersonalNamespaces[0].DirectorySeparator;
            }
        }

        public IImapFolder Inbox => new MailKitImapFolderAdapter(_client.Inbox);

        public IImapFolder GetPersonalRoot()
        {
            if (_client.PersonalNamespaces.Count == 0)
                throw new InvalidOperationException("No personal namespaces available.");

            var ns = _client.PersonalNamespaces[0];
            return new MailKitImapFolderAdapter(_client.GetFolder(ns));
        }

        public void Disconnect(bool quit)
        {
            _client.Disconnect(quit);
        }

        public void Dispose()
        {
            _client.Dispose();
        }
    }
}
