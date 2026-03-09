using System;
using System.IO;
using Npgsql;
using DotNetEnv;
using MailKit;

namespace MailDirectoryEngine.src.DB
{
    internal sealed class DBClientAdapter : IDBClient
    {
        public NpgsqlConnection? Connection { get; set; }

        

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

        public long? GetLastId()
        {
            using var cmd = new NpgsqlCommand("SELECT MAX(uid) FROM e_mails;", Connection);
            var result = cmd.ExecuteScalar();
            return result is null || result is DBNull ? null : Convert.ToInt64(result);
        }

        public void SetNewMessage(UniqueId uid,string hash, string path)
        {
            using var cmd = new NpgsqlCommand(
                "INSERT INTO e_mails(uid,hash, path) VALUES (@uid,@hash, @path);", Connection);
            cmd.Parameters.AddWithValue("@uid", (long)uid.Id);
            cmd.Parameters.AddWithValue("@hash", hash);
            cmd.Parameters.AddWithValue("@path", path);
            cmd.ExecuteNonQuery();
        }

        public void Dispose() => Connection?.Dispose();
    }
}
