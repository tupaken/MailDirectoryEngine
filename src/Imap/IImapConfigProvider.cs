namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Resolves IMAP account configuration by key.
    /// </summary>
    internal interface IImapConfigProvider
    {
        /// <summary>
        /// Retrieves an IMAP account configuration.
        /// </summary>
        /// <param name="key">Account key in the settings file.</param>
        /// <returns>Configuration for the requested account.</returns>
        ImapConfig GetConfig(string key);
        
        string GetSavePath();
    }
}
