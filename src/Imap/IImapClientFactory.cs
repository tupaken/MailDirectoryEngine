namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Creates configured IMAP client instances.
    /// </summary>
    internal interface IImapClientFactory
    {
        /// <summary>
        /// Creates and initializes an IMAP client for the provided account.
        /// </summary>
        /// <param name="config">IMAP account configuration.</param>
        /// <returns>A connected and authenticated IMAP client.</returns>
        IImapClient Create(ImapConfig config);
    }
}
