using MailKit;
using Npgsql;

namespace MailDirectoryEngine.src.DB
{
    /// <summary>
    /// Defines the database operations used by the mail processing flow.
    /// </summary>
    internal interface IDBClient : IDisposable
    {
        /// <summary>
        /// Gets or sets the open PostgreSQL connection used by the adapter.
        /// </summary>
        NpgsqlConnection? Connection { get; set; }

        /// <summary>
        /// Inserts a new inbox message record.
        /// </summary>
        /// <param name="hash">Deduplication hash of the inbox message.</param>
        /// <param name="content">Stored inbox message content.</param>
        void SetNewInboxMessage(string hash, string content);

        /// <summary>
        /// Checks whether an inbox message hash already exists.
        /// </summary>
        /// <param name="hash">Deduplication hash to search for.</param>
        /// <returns><c>true</c> when the hash already exists; otherwise <c>false</c>.</returns>
        bool CheckHashInbox(string hash);

        /// <summary>
        /// Inserts a new sent message record.
        /// </summary>
        /// <param name="hash">Deduplication hash of the sent message.</param>
        /// <param name="path">Persisted value stored in the sent message path column.</param>
        void SetNewSendMessage(string hash, string path);

        /// <summary>
        /// Checks whether a sent message hash already exists.
        /// </summary>
        /// <param name="hash">Deduplication hash to search for.</param>
        /// <returns><c>true</c> when the hash already exists; otherwise <c>false</c>.</returns>
        bool CheckHashSend(string hash);
    }
}
