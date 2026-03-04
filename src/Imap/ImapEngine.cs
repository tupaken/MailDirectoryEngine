using System;
using System.Linq;
using MailKit;

namespace MailDirectoryEngine.src.Imap
{
    class ImapEngine
    {
        private readonly IImapClientFactory _clientFactory;
        private readonly IImapConfigProvider _configProvider;
        private readonly string _accountKey;

        public ImapEngine()
            : this(
                new ImapService(),
                new JsonImapConfigProvider("./src/Imap/Imap_config.json"),
                "bewerbung")
        {
        }

        internal ImapEngine(IImapClientFactory clientFactory, IImapConfigProvider configProvider, string accountKey)
        {
            _clientFactory = clientFactory ?? throw new ArgumentNullException(nameof(clientFactory));
            _configProvider = configProvider ?? throw new ArgumentNullException(nameof(configProvider));
            if (string.IsNullOrWhiteSpace(accountKey))
                throw new ArgumentException("Account key is required.", nameof(accountKey));

            _accountKey = accountKey;
        }

        public int GetSendCount()
        {
            var client = this.CreateClient();
            try
            {
                var root = client.GetPersonalRoot();
                var separator = client.DirectorySeparator;

                var folders = root.GetSubfolders(true).ToList();

                var sent = folders.FirstOrDefault(f =>
                                string.Equals(f.Name, "Gesendete Elemente", StringComparison.Ordinal) ||
                                string.Equals(f.FullName, "Gesendete Elemente", StringComparison.Ordinal) ||
                                f.FullName.EndsWith($"{separator}Gesendete Elemente", StringComparison.Ordinal) ||
                                f.FullName.EndsWith($".Gesendete Elemente", StringComparison.Ordinal));

                if (sent == null)
                    throw new InvalidOperationException("Der Ordner 'Gesendete Elemente' wurde nicht gefunden.");

                sent.Open(FolderAccess.ReadOnly);
                return sent.Count;
            }
            finally
            {
                ClientDisconnect(client);
            }
        }

        public int GetInboxCount()
        {
            var client = this.CreateClient();
            try
            {
                var inbox = client.Inbox;

                inbox.Open(FolderAccess.ReadOnly);
                int count = inbox.Count;
                return count;
            }
            finally
            {
                ClientDisconnect(client);
            }
        }

        private IImapClient CreateClient()
        {
            var config = _configProvider.GetConfig(_accountKey);

            var client = _clientFactory.Create(config);
            return client;
        }

        private static void ClientDisconnect(IImapClient client)
        {
            client.Disconnect(true);
            client.Dispose();
        }
    }
}
