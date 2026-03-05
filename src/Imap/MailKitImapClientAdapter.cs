using System;
using MailKit.Net.Imap;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Adapter that wraps MailKit's <see cref="ImapClient"/> behind <see cref="IImapClient"/>.
    /// </summary>
    internal sealed class MailKitImapClientAdapter : IImapClient
    {
        private readonly ImapClient _client;

        /// <summary>
        /// Initializes a new adapter for the provided MailKit client.
        /// </summary>
        /// <param name="client">Underlying MailKit IMAP client.</param>
        public MailKitImapClientAdapter(ImapClient client)
        {
            _client = client ?? throw new ArgumentNullException(nameof(client));
        }

        /// <summary>
        /// Gets the personal namespace directory separator.
        /// </summary>
        /// <exception cref="InvalidOperationException">
        /// Thrown when no personal namespace is available.
        /// </exception>
        public char DirectorySeparator
        {
            get
            {
                if (_client.PersonalNamespaces.Count == 0)
                    throw new InvalidOperationException("No personal namespaces available.");

                return _client.PersonalNamespaces[0].DirectorySeparator;
            }
        }

        /// <summary>
        /// Gets the inbox folder adapter.
        /// </summary>
        public IImapFolder Inbox => new MailKitImapFolderAdapter(_client.Inbox);

        /// <summary>
        /// Gets the personal namespace root folder adapter.
        /// </summary>
        /// <returns>The personal root folder adapter.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown when no personal namespace is available.
        /// </exception>
        public IImapFolder GetPersonalRoot()
        {
            if (_client.PersonalNamespaces.Count == 0)
                throw new InvalidOperationException("No personal namespaces available.");

            var ns = _client.PersonalNamespaces[0];
            return new MailKitImapFolderAdapter(_client.GetFolder(ns));
        }

        /// <summary>
        /// Disconnects the underlying MailKit client.
        /// </summary>
        /// <param name="quit">True to end the session gracefully.</param>
        public void Disconnect(bool quit)
        {
            _client.Disconnect(quit);
        }

        /// <summary>
        /// Disposes the underlying MailKit client.
        /// </summary>
        public void Dispose()
        {
            _client.Dispose();
        }
    }
}
