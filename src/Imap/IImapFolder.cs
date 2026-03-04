using System.Collections.Generic;
using MailKit;

namespace MailDirectoryEngine.src.Imap
{
    internal interface IImapFolder
    {
        string Name { get; }
        string FullName { get; }
        int Count { get; }
        void Open(FolderAccess access);
        IEnumerable<IImapFolder> GetSubfolders(bool recursive);
    }
}
