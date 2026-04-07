using System;
using System.Security.Cryptography;
using System.Text;
using MailDirectoryEngine.src.DB;
using MailDirectoryEngine.src.Imap;
using MailKit;

namespace MailDirectoryEngine.src
{
    /// <summary>
    /// Application entry point and polling workflow for inbox and sent message processing.
    /// </summary>
    internal class Program
    {
        private const int DefaultInitialSyncLimit = 20;

        /// <summary>
        /// Reads the latest inbox and sent messages, deduplicates them by hash, and persists new entries.
        /// </summary>
        /// <param name="args">Unused command-line arguments.</param>
        static void Main(string[] args)
        {
            Console.WriteLine("Main:");
            List<String> users = ["bewerbung"];
            var accounts = new List <ImapEngine>() ;
            var db = new DB.DBClientAdapter();
            
            foreach (var i in users){
                var engine = new Imap.ImapEngine(i,ComputeHash(i));
                accounts.Add(engine);
            }
            while(true){
                foreach (var engine in accounts){
                    try{
                        engine.WithClient(client =>
                        {
                            var inbox = engine.GetInbox(client);
                            var allUidInbox = engine.GetAllUIDS(inbox);
                            InboxEMails(engine, db, inbox, allUidInbox);

                            var sent = engine.GetSent(client);
                            var allUidSent = engine.GetAllUIDS(sent);
                            SentEmails(engine, db, sent, allUidSent);
                        });
                    }catch(Exception ex)
                    {
                    Console.WriteLine("Fehler: " + ex.Message);   
                    }
                }
            }
        }

        /// <summary>
        /// Computes a SHA-256 hash for the provided text and returns it as an uppercase hexadecimal string.
        /// </summary>
        /// <param name="text">Message content to hash.</param>
        /// <returns>Uppercase hexadecimal SHA-256 digest.</returns>
        public static string ComputeHash(string text)
        {
            using var sha256 = SHA256.Create();
            byte[] bytes = Encoding.UTF8.GetBytes(text);
            byte[] hash = sha256.ComputeHash(bytes);
            return Convert.ToHexString(hash);
        }

        /// <summary>
        /// Persists all new inbox messages until a known hash is encountered.
        /// </summary>
        /// <param name="engine">IMAP engine used to load inbox messages.</param>
        /// <param name="db">Database client used for deduplication and persistence.</param>
        /// <param name="inbox">Opened inbox folder used for message reads.</param>
        /// <param name="Ids">Inbox UIDs in server order.</param>
        public static void InboxEMails(ImapEngine engine, DBClientAdapter db, IImapFolder inbox, IList<UniqueId> Ids)
        {
            if (Ids.Count == 0)
            {
                return;
            }

            var hashUS = engine.getAccountHash();
            var initialSyncLimit = ResolveInitialSyncLimit();
            var isInitialSync = !db.HasInboxRows(hashUS);
            var minIndex = (isInitialSync && initialSyncLimit > 0)
                ? Math.Max(0, Ids.Count - initialSyncLimit)
                : 0;
            var pendingMessages = new List<(string Hash, string Content)>();

            for (int i = Ids.Count - 1; i >= minIndex; i--)
            {
                var uid = Ids[i];
                var content = engine.GetMessage(inbox, uid).Context;
                var hash = ComputeHash(content);

                if (db.CheckHashInbox(hash, hashUS))
                {
                    break;
                }

                pendingMessages.Add((hash, content));
            }

            for (int i = pendingMessages.Count - 1; i >= 0; i--)
            {
                var pending = pendingMessages[i];
                db.SetNewInboxMessage(pending.Hash, pending.Content, hashUS);
            }
        }

        /// <summary>
        /// Persists all new sent messages until a known hash is encountered.
        /// </summary>
        /// <param name="engine">IMAP engine used to load sent messages.</param>
        /// <param name="db">Database client used for deduplication and persistence.</param>
        /// <param name="sent">Opened sent folder used for message reads and exports.</param>
        /// <param name="Ids">Sent message UIDs in server order.</param>
        public static void SentEmails(ImapEngine engine, DBClientAdapter db, IImapFolder sent, IList<UniqueId> Ids)
        {
            if (Ids.Count == 0)
            {
                return;
            }

            var hashUS = engine.getAccountHash();
            var initialSyncLimit = ResolveInitialSyncLimit();
            var isInitialSync = !db.HasSentRows(hashUS);
            var minIndex = (isInitialSync && initialSyncLimit > 0)
                ? Math.Max(0, Ids.Count - initialSyncLimit)
                : 0;
            var pendingMessages = new List<(UniqueId Uid, string Hash)>();

            for (int i = Ids.Count - 1; i >= minIndex; i--)
            {
                var uid = Ids[i];
                var content = engine.GetMessage(sent, uid).Context;
                var hash = ComputeHash(content);

                if (db.CheckHashSend(hash, hashUS))
                {
                    break;
                }

                pendingMessages.Add((uid, hash));
            }

            for (int i = pendingMessages.Count - 1; i >= 0; i--)
            {
                var pending = pendingMessages[i];
                var savedPath = engine.SaveMessage(sent, pending.Uid);
                db.SetNewSendMessage(pending.Hash, savedPath, hashUS);
            }
        }

        /// <summary>
        /// Resolves how many messages should be processed during initial synchronization.
        /// </summary>
        /// <returns>
        /// A positive limit value, or <see cref="DefaultInitialSyncLimit"/> when the environment value is missing/invalid.
        /// </returns>
        private static int ResolveInitialSyncLimit()
        {
            var envValue = Environment.GetEnvironmentVariable("INITIAL_SYNC_LIMIT");
            if (int.TryParse(envValue, out var parsed) && parsed > 0)
            {
                return parsed;
            }

            return DefaultInitialSyncLimit;
        }
    }
}
