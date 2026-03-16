using System;
using System.Linq;
using MailKit;
using MailKit.Search;

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

        private readonly string _accountHash;

        /// <summary>
        /// Initializes the engine with production defaults.
        /// </summary>
        /// <param name="accountKey">Account key resolved from configuration.</param>
        /// <param name="Hash">Account hash value used by the persistence flow.</param>
        public ImapEngine(string accountKey, string Hash)
            : this(
                new ImapService(),
                new JsonImapConfigProvider(Path.Combine(AppContext.BaseDirectory, "src", "Imap", "Imap_config.json")),
                accountKey,Hash)
        {
        }

        /// <summary>
        /// Initializes the engine with custom collaborators and account key.
        /// </summary>
        /// <param name="clientFactory">Factory used to create IMAP clients.</param>
        /// <param name="configProvider">Provider used to resolve account configuration.</param>
        /// <param name="accountKey">Account key resolved from configuration.</param>
        /// <param name="Hash">Account hash value used by the persistence flow.</param>
        internal ImapEngine(IImapClientFactory clientFactory, IImapConfigProvider configProvider, string accountKey,string Hash)
        {
            _clientFactory = clientFactory ?? throw new ArgumentNullException(nameof(clientFactory));
            _configProvider = configProvider ?? throw new ArgumentNullException(nameof(configProvider));
            if (string.IsNullOrWhiteSpace(accountKey))
                throw new ArgumentException("Account key is required.", nameof(accountKey));

            _accountKey = accountKey;
            _accountHash = Hash;
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
        /// Retrieves the newest message from the inbox as a lightweight DTO.
        /// </summary>
        /// <returns>
        /// A <see cref="MessageDto"/> containing UID, subject and message body.
        /// Returns an empty DTO with <see cref="UniqueId.Invalid"/> when inbox is empty.
        /// </returns>
        public MessageDto GetLastInboxMessage()
        {
            return UseClient(client => GetLatestMessage(GetInbox(client)));
        }

        /// <summary>
        /// Retrieves the newest message from the sent folder as a lightweight DTO.
        /// </summary>
        /// <returns>
        /// A <see cref="MessageDto"/> containing UID, subject and message body.
        /// Returns an empty DTO with <see cref="UniqueId.Invalid"/> when the sent folder is empty.
        /// </returns>
        public MessageDto GetLastSentMail()
        {
            return UseClient(client => GetLatestMessage(GetSent(client)));
        }

        /// <summary>
        /// Reads all message UIDs from the provided folder.
        /// </summary>
        /// <param name="folder">Opened IMAP folder.</param>
        /// <returns>List of UIDs in server order.</returns>
        public IList<UniqueId> GetAllUIDS(IImapFolder folder)
        {
            return folder.Search(SearchQuery.All);
        }


        /// <summary>
        /// Resolves the newest UID from a folder.
        /// </summary>
        /// <param name="fold">Opened IMAP folder.</param>
        /// <returns>Last UID, or null if folder is empty.</returns>
        public UniqueId? GetLastUID(IImapFolder fold)
        {
            var uids = GetAllUIDS(fold);
            if (uids.Count == 0)
            {
                return null;
            }
            var lastUid = uids[^1];
            return lastUid;
        }

        /// <summary>
        /// Opens and returns the inbox folder in read-only mode.
        /// </summary>
        /// <param name="client">Connected IMAP client.</param>
        /// <returns>Opened inbox folder abstraction.</returns>
        public IImapFolder GetInbox(IImapClient client)
        {
            var inbox = client.Inbox;
            inbox.Open(FolderAccess.ReadOnly);
            return inbox;
        }

        /// <summary>
        /// Locates and opens the sent folder in read-only mode.
        /// </summary>
        /// <param name="client">Connected IMAP client.</param>
        /// <returns>Opened sent folder abstraction.</returns>
        /// <exception cref="InvalidOperationException"></exception>
        public IImapFolder GetSent(IImapClient client)
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
                throw new InvalidOperationException("Sent folder 'Gesendete Elemente' was not found.");
            sent.Open(FolderAccess.ReadOnly);
            return sent;
        }

        /// <summary>
        /// Exports the specified inbox message as an <c>.eml</c> file.
        /// </summary>
        /// <param name="uid">UID of the inbox message to export.</param>
        /// <exception cref="InvalidOperationException">
        /// Thrown when no save path is configured.
        /// </exception>
        public string SaveInboxMail(UniqueId uid)
        {
            return UseClient(client => SaveMail(GetInbox(client), uid));
        }

        /// <summary>
        /// Exports the specified sent message as an <c>.eml</c> file.
        /// </summary>
        /// <param name="uid">UID of the sent message to export.</param>
        /// <exception cref="InvalidOperationException">
        /// Thrown when no save path is configured.
        /// </exception>
        public string SaveSentMail(UniqueId uid)
        {
            return UseClient(client => SaveMail(GetSent(client), uid));
        }

        /// <summary>
        /// Creates a client, executes the supplied action, and always disconnects the client afterwards.
        /// </summary>
        /// <typeparam name="T">Return type of the action.</typeparam>
        /// <param name="action">Operation executed against the created client.</param>
        /// <returns>Result produced by <paramref name="action"/>.</returns>
        private T UseClient<T>(Func<IImapClient, T> action)
        {
            var client = CreateClient();
            try
            {
                return action(client);
            }
            finally
            {
                ClientDisconnect(client);
            }
        }

        /// <summary>
        /// Loads the newest message from an opened folder.
        /// </summary>
        /// <param name="folder">Folder to inspect.</param>
        /// <returns>
        /// Latest message converted to <see cref="MessageDto"/>, or an empty DTO with <see cref="UniqueId.Invalid"/>
        /// when the folder contains no messages.
        /// </returns>
        private MessageDto GetLatestMessage(IImapFolder folder)
        {
            var lastUid = GetLastUID(folder);
            if (lastUid is null)
            {
                return new MessageDto(UniqueId.Invalid, "", "");
            }

            var message = folder.GetMessage(lastUid.Value);
            return CreateMessageDto(lastUid.Value, message);
        }

        /// <summary>
        /// Projects a MIME message into the lightweight message DTO used by the application.
        /// </summary>
        /// <param name="uid">Unique identifier of the message.</param>
        /// <param name="message">MIME message returned by MailKit.</param>
        /// <returns>DTO containing UID, subject, and preferred body content.</returns>
        private static MessageDto CreateMessageDto(UniqueId uid, MimeKit.MimeMessage message)
        {
            return new MessageDto(
                uid,
                message.Subject ?? "",
                message.HtmlBody ?? message.TextBody ?? "");
        }

        /// <summary>
        /// Saves the specified message from a folder as an <c>.eml</c> file in the configured export directory.
        /// </summary>
        /// <param name="folder">Folder containing the message.</param>
        /// <param name="uid">Unique identifier of the message to export.</param>
        /// <returns>Full path to the written <c>.eml</c> file.</returns>
        private string SaveMail(IImapFolder folder, UniqueId uid)
        {
            var message = folder.GetMessage(uid);
            var filePath = Path.Combine(GetSaveDirectory(), $"{uid.Id}.eml");

            using var fileStream = File.Create(filePath);
            message.WriteTo(fileStream);

            return filePath;
        }

        /// <summary>
        /// Resolves and creates the export directory used for saved mail files.
        /// </summary>
        /// <returns>Absolute path to the export directory.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown when no save path is configured.
        /// </exception>
        private string GetSaveDirectory()
        {
            var directory = _configProvider.GetSavePath();
            if (string.IsNullOrWhiteSpace(directory))
                throw new InvalidOperationException("SavePath is not specified");

            directory = Path.GetFullPath(Environment.ExpandEnvironmentVariables(directory));
            Directory.CreateDirectory(directory);
            return directory;
        }

        /// <summary>
        /// Reads all UIDs currently available in the inbox.
        /// </summary>
        /// <returns>Inbox message UIDs in server order.</returns>
        public IList<UniqueId> GetAllUIDInbox()
        {
            return UseClient(client => GetAllUIDS(GetInbox(client)));
        }

        /// <summary>
        /// Reads all UIDs currently available in the sent folder.
        /// </summary>
        /// <returns>Sent message UIDs in server order.</returns>
        public IList<UniqueId> GetAllUIDSent()
        {
            return UseClient(client => GetAllUIDS(GetSent(client)));
        }

        /// <summary>
        /// Loads a specific inbox message while the IMAP client is still connected.
        /// </summary>
        /// <param name="id">UID of the inbox message to load.</param>
        /// <returns>Loaded inbox message as a DTO.</returns>
        public MessageDto GetInboxMessage(UniqueId id)
        {
            return UseClient(client =>
            {
                var inbox = GetInbox(client);
                var message = inbox.GetMessage(id);
                return CreateMessageDto(id, message);
            });
        }

        /// <summary>
        /// Loads a specific sent message while the IMAP client is still connected.
        /// </summary>
        /// <param name="id">UID of the sent message to load.</param>
        /// <returns>Loaded sent message as a DTO.</returns>
        public MessageDto GetSentMessage(UniqueId id)
        {
            return UseClient(client =>
            {
                var sent = GetSent(client);
                var message = sent.GetMessage(id);
                return CreateMessageDto(id, message);
            });
        }

        /// <summary>
        /// Returns the account hash used for account-scoped deduplication checks.
        /// </summary>
        /// <returns>Account hash value for the current engine instance.</returns>
        public string getAccountHash()
        {
            return _accountHash;
        }

    }
}
