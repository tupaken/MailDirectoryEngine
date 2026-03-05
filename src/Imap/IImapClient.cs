using System;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Minimal abstraction over an IMAP client used by the engine.
    /// </summary>
    internal interface IImapClient : IDisposable
    {
        /// <summary>
        /// Gets the directory separator used by the server namespace.
        /// </summary>
        char DirectorySeparator { get; }

        /// <summary>
        /// Gets the inbox folder.
        /// </summary>
        IImapFolder Inbox { get; }

        /// <summary>
        /// Gets the personal namespace root folder.
        /// </summary>
        /// <returns>The personal root folder.</returns>
        IImapFolder GetPersonalRoot();

        /// <summary>
        /// Disconnects from the IMAP server.
        /// </summary>
        /// <param name="quit">
        /// True to gracefully end the IMAP session; otherwise false.
        /// </param>
        void Disconnect(bool quit);
    }
}
