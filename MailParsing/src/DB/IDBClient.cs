using MailKit;
using Npgsql;

namespace MailDirectoryEngine.src.DB
{
    internal interface IDBClient
    {
        NpgsqlConnection? Connection { get; set; }

        long? GetLastId();

        void SetNewMessage(UniqueId uid ,string hash, string path);

        void Dispose();
    }
}
