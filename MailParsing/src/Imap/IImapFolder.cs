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
        /// Searches the folder for messages matching the provided query.
        /// </summary>
        /// <param name="query">MailKit search query.</param>
        /// <returns>Matching message UIDs in server order.</returns>
        IList<UniqueId> Search(SearchQuery query);

        /// <summary>
        /// Loads a single message by UID from the opened folder.
        /// </summary>
        /// <param name="uid">Unique message identifier.</param>
        /// <returns>The fully parsed MIME message.</returns>
        MimeMessage GetMessage(UniqueId uid);
    }
}
