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

        public static string ComputeHash(string text)
        {
            using var sha256 = SHA256.Create();
            byte[] bytes = Encoding.UTF8.GetBytes(text);
            byte[] hash = sha256.ComputeHash(bytes);
            return Convert.ToHexString(hash);
        }
    }
}
