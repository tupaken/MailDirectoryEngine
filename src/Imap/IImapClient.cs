using System;

namespace MailDirectoryEngine.src.Imap
{
    internal interface IImapClient : IDisposable
    {
        char DirectorySeparator { get; }
        IImapFolder Inbox { get; }
        IImapFolder GetPersonalRoot();
        void Disconnect(bool quit);
    }
}
