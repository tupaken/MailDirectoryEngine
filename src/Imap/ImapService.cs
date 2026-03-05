using System;
using MailKit.Net.Imap;
using MailKit.Security;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Creates and initializes MailKit-based IMAP client instances.
    /// </summary>
    internal class ImapService : IImapClientFactory
    {
        private readonly Func<ImapClient> _clientFactory;

        /// <summary>
        /// Initializes the service with the default MailKit client factory.
        /// </summary>
        public ImapService()
            : this(() => new ImapClient())
        {
        }

        /// <summary>
        /// Initializes the service with a custom MailKit client factory.
        /// </summary>
        /// <param name="clientFactory">Factory used to create <see cref="ImapClient"/> instances.</param>
        internal ImapService(Func<ImapClient> clientFactory)
        {
            _clientFactory = clientFactory ?? throw new ArgumentNullException(nameof(clientFactory));
        }

        /// <summary>
        /// Creates a connected and authenticated IMAP client adapter.
        /// </summary>
        /// <param name="config">Account configuration used for connect and authentication.</param>
        /// <returns>A configured IMAP client adapter.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown when connect or authentication fails.
        /// </exception>
        public IImapClient Create(ImapConfig config)
        {
            if (config == null)
                throw new ArgumentNullException(nameof(config));

            var client = _clientFactory();
            try
            {
                ConnectAndAuthenticate(client, config);
            }
            catch (Exception ex)
            {
                client.Dispose();
                throw new InvalidOperationException(
                    $"IMAP Connect/Auth fehlgeschlagen fuer '{config.User}'.",
                    ex);
            }

            return new MailKitImapClientAdapter(client);
        }

        /// <summary>
        /// Connects and authenticates the underlying MailKit IMAP client.
        /// </summary>
        /// <param name="client">MailKit IMAP client instance.</param>
        /// <param name="config">Account configuration values.</param>
        internal virtual void ConnectAndAuthenticate(ImapClient client, ImapConfig config)
        {
            client.Connect(config.Host, config.Port, SecureSocketOptions.SslOnConnect);
            client.Authenticate(config.User, config.Password);
        }
    }
}
