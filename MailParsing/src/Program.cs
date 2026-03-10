using System;
using System.Security.Cryptography;
using System.Text;
using MailKit;

namespace MailDirectoryEngine.src
{
    internal class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Main:");
            var engine = new Imap.ImapEngine();
            var inboxMessage = engine.GetLastInboxMessage();

            if (inboxMessage.Uid == UniqueId.Invalid)
            {
                Console.WriteLine("Keine Inbox-Nachricht gefunden.");
                return;
            }

            var inboxFilePath = engine.SaveInboxMail(inboxMessage.Uid);
            var sentMessage = engine.GetLastSentMail();

            if (sentMessage.Uid != UniqueId.Invalid)
            {
                engine.SaveSentMail(sentMessage.Uid);
            }

            using var db = new DB.DBClientAdapter();
            db.SetNewMessage(
                inboxMessage.Uid,
                ComputeHash(inboxMessage.Context),
                inboxFilePath);
        }

        public static string ComputeHash(string text)
        {
            using var sha256 = SHA256.Create();
            byte[] bytes = Encoding.UTF8.GetBytes(text);
            byte[] hash = sha256.ComputeHash(bytes);
            return Convert.ToHexString(hash);
        }
    }
}
