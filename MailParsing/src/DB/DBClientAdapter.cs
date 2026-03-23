using System;
using System.IO;
using Npgsql;
using DotNetEnv;

namespace MailDirectoryEngine.src.DB
{
    /// <summary>
    /// PostgreSQL-backed implementation of the mail persistence contract.
    /// </summary>
    internal sealed class DBClientAdapter : IDBClient
    {
        /// <summary>
        /// Gets or sets the open PostgreSQL connection used by the adapter.
        /// </summary>
        public NpgsqlConnection? Connection { get; set; }

        string inbox= "e_mails_inbox";
        string send="e_mails_send";

        /// <summary>
        /// Initializes the adapter, loads environment variables from the repository root, and opens the database connection.
        /// </summary>
        public DBClientAdapter()
        {
            var envPath = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".env"));
            if (File.Exists(envPath))
            {
                Env.Load(envPath);
            }

            var ConnectionString = new NpgsqlConnectionStringBuilder{
                Host = "localhost", 
                Port = int.Parse(Environment.GetEnvironmentVariable("POSTGRES_PORT") ?? "5432"),
                Database = Environment.GetEnvironmentVariable("POSTGRES_DB"),
                Username = Environment.GetEnvironmentVariable("POSTGRES_USER"),
                Password = Environment.GetEnvironmentVariable("POSTGRES_PASSWORD")
                }.ToString();
            Connection = new NpgsqlConnection(ConnectionString);
            Connection.Open();
        }
    

        /// <summary>
        /// Inserts a new inbox message row into the inbox table.
        /// </summary>
        /// <param name="hash">Deduplication hash of the inbox message.</param>
        /// <param name="content">Message content stored with the inbox record.</param>
        /// <param name="account">Account scope identifier stored with the inbox record.</param>
        public void SetNewInboxMessage(string hash, string content,string account)
        {
            using var cmd = new NpgsqlCommand(
                $"INSERT INTO {inbox}(hash,content,account) VALUES (@hash, @content, @account);", Connection);
            cmd.Parameters.AddWithValue("@hash", hash);
            cmd.Parameters.AddWithValue("@content", content);
            cmd.Parameters.AddWithValue("@account",account);
            cmd.ExecuteNonQuery();
        }

        /// <summary>
        /// Checks whether the inbox table already contains the provided hash.
        /// </summary>
        /// <param name="hash">Deduplication hash to search for.</param>
        /// <param name="account">Account scope identifier used for the lookup.</param>
        /// <returns><c>true</c> when the hash already exists; otherwise <c>false</c>.</returns>
        public bool  CheckHashInbox(string hash,string account)
        {
            using var cmd = new NpgsqlCommand(
                $"SELECT EXISTS (SELECT 1 FROM {inbox} WHERE hash = @hash and account = @account);"
                ,Connection);
            cmd.Parameters.AddWithValue("@hash", hash);
            cmd.Parameters.AddWithValue("@account", account);
            return (bool)cmd.ExecuteScalar() ? true:false;
        }

        
        /// <summary>
        /// Disposes the open database connection.
        /// </summary>
        public void Dispose() => Connection?.Dispose();

        /// <summary>
        /// Inserts a new sent message row into the sent table.
        /// </summary>
        /// <param name="hash">Deduplication hash of the sent message.</param>
        /// <param name="path">Path value stored for the sent message record.</param>
        /// <param name="account">Account scope identifier stored with the sent record.</param>
        public void SetNewSendMessage(string hash, string path, string account)
        {
            using var cmd = new NpgsqlCommand(
                $"INSERT INTO {send}(hash,path,account) VALUES (@hash, @path, @account);",
            Connection);
            cmd.Parameters.AddWithValue("@hash",hash);
            cmd.Parameters.AddWithValue("@path",path);
            cmd.Parameters.AddWithValue("@account",account);
            cmd.ExecuteNonQuery();
        }

        /// <summary>
        /// Checks whether the sent table already contains the provided hash.
        /// </summary>
        /// <param name="hash">Deduplication hash to search for.</param>
        /// <param name="account">Account scope identifier used for the lookup.</param>
        /// <returns><c>true</c> when the hash already exists; otherwise <c>false</c>.</returns>
        public bool CheckHashSend(string hash,string account)
        {
            using var cmd = new NpgsqlCommand(
                $"SELECT EXISTS (SELECT 1 FROM {send} WHERE hash = @hash and account=@account);"
                ,Connection);
            cmd.Parameters.AddWithValue("@hash", hash);
            cmd.Parameters.AddWithValue("@account",account);
            return (bool)cmd.ExecuteScalar();
        }

    }
}
