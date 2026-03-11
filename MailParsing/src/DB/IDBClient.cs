using MailKit;
using Npgsql;

namespace MailDirectoryEngine.src.DB
{
    internal interface IDBClient : IDisposable
    {
        NpgsqlConnection? Connection { get; set; }

        void SetNewInboxMessage(string hash, string content);

        bool CheckHashInbox(string hash);

        void SetNewSendMessage(string hash, string path);

        bool CheckHashSend(string hash);
    }
}
