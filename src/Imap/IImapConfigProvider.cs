namespace MailDirectoryEngine.src.Imap
{
    internal interface IImapConfigProvider
    {
        ImapConfig GetConfig(string key);
    }
}
