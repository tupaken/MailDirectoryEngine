using System;
using System.Collections.Generic;
using System.Linq;
using MailKit;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Adapter that wraps MailKit's <see cref="IMailFolder"/> behind <see cref="IImapFolder"/>.
    /// </summary>
    internal sealed class MailKitImapFolderAdapter : IImapFolder
    {
        private readonly IMailFolder _folder;

        /// <summary>
        /// Initializes a new folder adapter.
        /// </summary>
        /// <param name="folder">Underlying MailKit folder.</param>
        public MailKitImapFolderAdapter(IMailFolder folder)
        {
            _folder = folder ?? throw new ArgumentNullException(nameof(folder));
        }

        /// <summary>
        /// Gets the display name of the folder.
        /// </summary>
        public string Name => _folder.Name;

        /// <summary>
        /// Gets the full folder path as provided by the server.
        /// </summary>
        public string FullName => _folder.FullName;

        /// <summary>
        /// Gets the number of messages in the folder.
        /// </summary>
        public int Count => _folder.Count;

        /// <summary>
        /// Opens the folder with the given access mode.
        /// </summary>
        /// <param name="access">Folder access level.</param>
        public void Open(FolderAccess access)
        {
            _folder.Open(access);
        }

        /// <summary>
        /// Gets subfolders and adapts them to <see cref="IImapFolder"/>.
        /// </summary>
        /// <param name="recursive">
        /// True to include nested subfolders recursively; otherwise only direct children.
        /// </param>
        /// <returns>Adapted subfolder sequence.</returns>
        public IEnumerable<IImapFolder> GetSubfolders(bool recursive)
        {
            return _folder.GetSubfolders(recursive).Select(f => new MailKitImapFolderAdapter(f));
        }
    }
}
