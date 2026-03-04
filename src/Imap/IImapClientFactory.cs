namespace MailDirectoryEngine.src.Imap
{
    internal interface IImapClientFactory
    {
        IImapClient Create(ImapConfig config);
    }
}
