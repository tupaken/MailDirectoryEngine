using System;
using System.Linq;
using MailKit;
using MailKit.Search;
using Org.BouncyCastle.Security;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// High-level IMAP operations used by the application.
    /// </summary>
    class ImapEngine
    {
        private readonly IImapClientFactory _clientFactory;
        private readonly IImapConfigProvider _configProvider;
        private readonly string _accountKey;

        /// <summary>
        /// Initializes the engine with production defaults.
        /// </summary>
        public ImapEngine()
            : this(
                new ImapService(),
                new JsonImapConfigProvider("./src/Imap/Imap_config.json"),
                "bewerbung")
        {
        }

        /// <summary>
        /// Initializes the engine with custom collaborators and account key.
        /// </summary>
        /// <param name="clientFactory">Factory used to create IMAP clients.</param>
        /// <param name="configProvider">Provider used to resolve account configuration.</param>
        /// <param name="accountKey">Account key resolved from configuration.</param>
        internal ImapEngine(IImapClientFactory clientFactory, IImapConfigProvider configProvider, string accountKey)
        {
            _clientFactory = clientFactory ?? throw new ArgumentNullException(nameof(clientFactory));
            _configProvider = configProvider ?? throw new ArgumentNullException(nameof(configProvider));
            if (string.IsNullOrWhiteSpace(accountKey))
                throw new ArgumentException("Account key is required.", nameof(accountKey));

            _accountKey = accountKey;
        }

        /// <summary>
        /// Gets the message count from the sent items folder.
        /// </summary>
        /// <returns>Number of messages in sent items.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown when no sent items folder can be found.
        /// </exception>
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

        /// <summary>
        /// Gets the message count from the inbox folder.
        /// </summary>
        /// <returns>Number of messages in inbox.</returns>
        public int GetInboxCount()
        {
            var client = this.CreateClient();
            try
            {
                var inbox = GetInbox(client);
                int count = inbox.Count;
                return count;
            }
            finally
            {
                ClientDisconnect(client);
            }
        }

        /// <summary>
        /// Creates an IMAP client for the configured account key.
        /// </summary>
        /// <returns>A connected and authenticated IMAP client.</returns>
        private IImapClient CreateClient()
        {
            var config = _configProvider.GetConfig(_accountKey);

            var client = _clientFactory.Create(config);
            return client;
        }

        /// <summary>
        /// Gracefully disconnects and disposes the IMAP client.
        /// </summary>
        /// <param name="client">Client to disconnect and dispose.</param>
        private static void ClientDisconnect(IImapClient client)
        {
            client.Disconnect(true);
            client.Dispose();
        }


        /// <summary>
        /// Get last Message in Inbox  
        /// </summary>
        /// <returns> UID, Titel, Context </returns>
        public MessageDto? GetLastInboxMessage(){
            
            var client = this.CreateClient();
            UniqueId? lastUid = null;
            MimeKit.MimeMessage? message = null;
            try
            {
                var inbox = GetInbox(client);
                
                lastUid = this.GetLastUID(inbox);

                if (lastUid is null)
                {
                    return new MessageDto(UniqueId.Invalid,"","");
                }
                message = inbox.GetMessage(lastUid.Value);

            }
            finally
            {
                ClientDisconnect(client);
            }
            
            return new MessageDto(lastUid.Value,
            message.Subject ?? "",message.HtmlBody ?? message.TextBody ?? "");
        }

        /// <summary>
        /// Get all Uids
        /// </summary>
        /// <param name="inbox"></param>
        /// <returns></returns>
        private IList<UniqueId> GetAllUIDS(IImapFolder folder)
        {   
            return folder.Search(SearchQuery.All);
        }


        /// <summary>
        /// Get last UID in folder
        /// </summary>
        /// <param name="inbox"></param>
        /// <returns></returns>
        private UniqueId? GetLastUID(IImapFolder fold)
        {
            var uids = GetAllUIDS(fold);
            if (uids.Count == 0)
            {
                return null;
            }
            var lastUid=uids[^1];
            return lastUid;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="uid"></param>
        /// <exception cref="InvalidOperationException"></exception>
        public void SaveInboxMail(UniqueId uid)
        {
            var client = this.CreateClient();
            try{
                var inbox = this.GetInbox(client);
                var msg = inbox.GetMessage(uid);
                var dir = _configProvider.GetSavePath();
                if (string.IsNullOrWhiteSpace(dir))
                    throw new InvalidOperationException("SavePath is not specified");
                dir = Path.GetFullPath(Environment.ExpandEnvironmentVariables(dir));
                Directory.CreateDirectory(dir);

                var filePath = Path.Combine(dir, $"{uid.Id}.eml");
                using var fs = File.Create(filePath);
                msg.WriteTo(fs);
            }
            finally{
                ClientDisconnect(client);
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="client"></param>
        /// <returns></returns>
        private IImapFolder GetInbox(IImapClient client)
        {
            var inbox=client.Inbox;
            inbox.Open(FolderAccess.ReadOnly);
            return inbox;
        }
    }
}
