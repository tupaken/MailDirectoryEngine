using System;
using System.IO;
using System.Text.Json;
using System.Runtime.CompilerServices;
using MailDirectoryEngine.src;
using MailKit;
using MailKit.Net.Imap;
using MailKit.Security;
using MimeKit;
using MailDirectoryEngine.src.Imap;

namespace MailDirectoryEngine.src.Imap{

    class ImapEngine
    {

        public int GetSendCount() {

            var client = this.CreateClient();

            var ns = client.PersonalNamespaces[0];
            var root = client.GetFolder(ns);

            var folders = root.GetSubfolders(true).ToList();

            var sent = folders.FirstOrDefault(f =>
                            string.Equals(f.Name, "Gesendete Elemente", StringComparison.Ordinal) ||
                            string.Equals(f.FullName, "Gesendete Elemente", StringComparison.Ordinal) ||
                            f.FullName.EndsWith($"{ns.DirectorySeparator}Gesendete Elemente", StringComparison.Ordinal) ||
                            f.FullName.EndsWith($".Gesendete Elemente", StringComparison.Ordinal));

            sent.Open(FolderAccess.ReadOnly);

            this.ClientDisconnect(client);

            return sent.Count;
        }

        public int GetInboxCount() {

            var client = this.CreateClient();

            var inbox = client.Inbox;

            inbox.Open(FolderAccess.ReadOnly);
            int count = inbox.Count;
            this.ClientDisconnect(client);
            return count;
        }


        /// <summary>
        /// Creates and returns a connected and authenticated IMAP client using the current configuration.
        /// </summary>
        /// <remarks>
        /// The returned <see cref="ImapClient"/> is already connected and authenticated.
        /// The caller is responsible for properly closing and disposing the client after use,
        /// typically by calling <see cref="ImapClient.Disconnect(bool)"/> and
        /// <see cref="IDisposable.Dispose"/>, or by using a <c>using</c> statement.
        /// </remarks>
        /// <returns>
        /// A connected and authenticated <see cref="ImapClient"/> instance.
        /// </returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown if required configuration values in <see cref="ImapConfig"/> are missing
        /// (for example Host, Port, User, or Password) or if the connection/authentication fails.
        /// </exception>
        private ImapClient CreateClient()
        {
            var config = this.ReadConfig("bewerbung");
          

            var imapService = new ImapService();

            var client = imapService.CreateClient(config);
            return client;
        }

        private void ClientDisconnect(ImapClient client)
        {
            client.Disconnect(true);
            client.Dispose();
        }

        private ImapConfig ReadConfig(string key)
        {
            var settings = ConfigLoader.Load("./src/Imap/Imap_config.json");
            if (!settings.Accounts.TryGetValue(key, out var config))
                throw new ArgumentException($"Unknown account key: '{key}'", nameof(key));

            return config;
        }
    }
}   
