using System;
using System.Security.Cryptography;
using System.Text;
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

            var lastIM=engine.GetLastInboxMessage().Context;
            var hashIM=ComputeHash(lastIM);
            if (!db.CheckHashInbox(hashIM))
            {
                db.SetNewInboxMessage(hashIM,lastIM);
            }

            var lastSM=engine.GetLastSentMail();
            var hashSM=ComputeHash(lastSM.Context);
            if (!db.CheckHashSend(hashSM))
            {
                engine.SaveSentMail(lastSM.Uid);
                db.SetNewSendMessage(hashSM,hashSM);
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
    }
}
