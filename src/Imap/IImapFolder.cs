using System.Collections.Generic;
using MailKit;
using MailKit.Search;
using MimeKit;

namespace MailDirectoryEngine.src.Imap
{
    /// <summary>
    /// Minimal abstraction over an IMAP folder.
    /// </summary>
    internal interface IImapFolder
    {
        /// <summary>
        /// Gets the display name of the folder.
        /// </summary>
        string Name { get; }

        /// <summary>
        /// Gets the full server path of the folder.
        /// </summary>
        string FullName { get; }

        /// <summary>
        /// Gets the number of messages in the folder.
        /// </summary>
        int Count { get; }

        /// <summary>
        /// Opens the folder with the requested access mode.
        /// </summary>
        /// <param name="access">Requested folder access level.</param>
        void Open(FolderAccess access);

        /// <summary>
        /// Returns subfolders of the current folder.
        /// </summary>
        /// <param name="recursive">
        /// True to return nested subfolders recursively; otherwise only direct children.
        /// </param>
        /// <returns>Sequence of subfolders.</returns>
        IEnumerable<IImapFolder> GetSubfolders(bool recursive);
        /// <summary>
        /// 
        /// </summary>
        /// <param name="query"></param>
        /// <returns></returns>
        IList<UniqueId> Search(SearchQuery query);

        MimeMessage GetMessage(UniqueId uid);
    }
}
