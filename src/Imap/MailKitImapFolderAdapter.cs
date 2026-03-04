using System;
using System.Collections.Generic;
using System.Linq;
using MailKit;

namespace MailDirectoryEngine.src.Imap
{
    internal sealed class MailKitImapFolderAdapter : IImapFolder
    {
        private readonly IMailFolder _folder;

        public MailKitImapFolderAdapter(IMailFolder folder)
        {
            _folder = folder ?? throw new ArgumentNullException(nameof(folder));
        }

        public string Name => _folder.Name;
        public string FullName => _folder.FullName;
        public int Count => _folder.Count;

        public void Open(FolderAccess access)
        {
            _folder.Open(access);
        }

        public IEnumerable<IImapFolder> GetSubfolders(bool recursive)
        {
            return _folder.GetSubfolders(recursive).Select(f => new MailKitImapFolderAdapter(f));
        }
    }
}
