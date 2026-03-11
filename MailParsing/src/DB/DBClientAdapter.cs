using System;
using System.IO;
using Npgsql;
using DotNetEnv;
using MailKit;
using Microsoft.VisualBasic;

namespace MailDirectoryEngine.src.DB
{
    internal sealed class DBClientAdapter : IDBClient
    {
        public NpgsqlConnection? Connection { get; set; }

        string inbox= "e_mails_inbox";
        string send="e_mails_send";

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
    

        public void SetNewInboxMessage(string hash, string content)
        {
            using var cmd = new NpgsqlCommand(
                $"INSERT INTO {inbox}(hash,content) VALUES (@hash, @content);", Connection);
            cmd.Parameters.AddWithValue("@hash", hash);
            cmd.Parameters.AddWithValue("@content", content);
            cmd.ExecuteNonQuery();
        }

        public bool  CheckHashInbox(string hash)
        {
            using var cmd = new NpgsqlCommand(
                $"SELECT EXISTS (SELECT 1 FROM {inbox} WHERE hash = @hash);"
                ,Connection);
            cmd.Parameters.AddWithValue("@hash", hash);
            
            return (bool)cmd.ExecuteScalar() ? true:false;
        }

        
        public void Dispose() => Connection?.Dispose();

        public void SetNewSendMessage(string hash, string path)
        {
            using var cmd = new NpgsqlCommand(
                $"INSERT INTO {send}(hash,path) VALUES (@hash, @path);",
            Connection);
            cmd.Parameters.AddWithValue("@hash",hash);
            cmd.Parameters.AddWithValue("@path",path);
            cmd.ExecuteNonQuery();
        }

        public bool CheckHashSend(string hash)
        {
            using var cmd = new NpgsqlCommand(
                $"SELECT EXISTS (SELECT 1 FROM {send} WHERE hash = @hash);"
                ,Connection);
            cmd.Parameters.AddWithValue("@hash", hash);
            return (bool)cmd.ExecuteScalar();
        }

    }
}
