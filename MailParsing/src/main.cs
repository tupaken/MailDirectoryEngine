using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using MailKit;

namespace MailDirectoryEngine.src
{
    internal class main
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Main:");
            var engine = new Imap.ImapEngine();
            var db = new DB.DBClientAdapter();
            var inboxMessage = engine.GetLastInboxMessage();
            var sentMessage = engine.GetLastSentMail();

            if (inboxMessage is null || inboxMessage.Uid == UniqueId.Invalid)
            {
                Console.WriteLine("Keine Inbox-Nachricht gefunden.");
                return;
            }

            Console.WriteLine("Gesendet: " + engine.GetSendCount());
            Console.WriteLine("Postengang: " + engine.GetInboxCount());
            Console.WriteLine("UID " + inboxMessage.Uid);
            Console.WriteLine("Context " + inboxMessage.Context);
            Console.WriteLine("Titel " + inboxMessage.Titel);
            engine.SaveInboxMail(inboxMessage.Uid);

            if (sentMessage is not null && sentMessage.Uid != UniqueId.Invalid)
            {
                engine.SaveSentMail(sentMessage.Uid);
            }

            db.SetNewMessage(
                inboxMessage.Uid,
                ComputeHash(inboxMessage.Context),
                $"fghfh/dhfghf/ddghfh/{inboxMessage.Uid}.eml");
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
