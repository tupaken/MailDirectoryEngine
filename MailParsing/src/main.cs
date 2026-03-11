using System;
using System.Security.Cryptography;
using System.Text;
using MailDirectoryEngine.src.DB;
using MailDirectoryEngine.src.Imap;
using MailKit;

namespace MailDirectoryEngine.src
{
    internal class Program
    {
        /// <summary>
        /// Reads the latest inbox and sent messages, deduplicates them by hash, and persists new entries.
        /// </summary>
        /// <param name="args">Unused command-line arguments.</param>
        static void Main(string[] args)
        {
            Console.WriteLine("Main:");
            var engine = new Imap.ImapEngine();
            var db = new DB.DBClientAdapter();

            var allUidInbox=engine.GetAllUIDInbox();
            InboxEMails(engine,db,allUidInbox);

            var allUidSent = engine.GetAllUIDSent();
            SentEmails(engine,db,allUidSent);
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
        /// <param name="Ids">Inbox UIDs in server order.</param>
        public static void InboxEMails(ImapEngine engine, DBClientAdapter db,IList<UniqueId> Ids)
        {
            if (Ids.Count == 0)
            {
                return;
            }

            var IMId=Ids[^1];
            var IMCont=engine.GetInboxMessage(IMId).Context;
            var hashIM=ComputeHash(IMCont);
            if (!db.CheckHashInbox(hashIM))
            {   
                var newIds =Ids.Take(Ids.Count - 1).ToList();
                InboxEMails(engine,db,newIds);
                db.SetNewInboxMessage(hashIM,IMCont);
            }
        }

        /// <summary>
        /// Persists all new sent messages until a known hash is encountered.
        /// </summary>
        /// <param name="engine">IMAP engine used to load sent messages.</param>
        /// <param name="db">Database client used for deduplication and persistence.</param>
        /// <param name="Ids">Sent message UIDs in server order.</param>
        public static void SentEmails(ImapEngine engine, DBClientAdapter db,IList<UniqueId> Ids)
        {
            if (Ids.Count == 0)
            {
                return;
            }

            var SId=Ids[^1];
            var SCont=engine.GetSentMessage(SId).Context;
            var hashIM=ComputeHash(SCont);
            if (!db.CheckHashSend(hashIM))
            {   
                var newIds =Ids.Take(Ids.Count - 1).ToList();
                SentEmails(engine,db,newIds);
                db.SetNewSendMessage(hashIM,SCont);
            }
        }
    }
}
