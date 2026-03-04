using System;
using System.Collections.Generic;
using System.Text;
using MimeKit.Cryptography;

namespace MailDirectoryEngine.src
{
    internal class main
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Main:");
            var engine = new Imap.ImapEngine();
            Console.WriteLine("Gesendet: " + engine.GetSendCount());
            Console.WriteLine("Postengang: " + engine.GetInboxCount());

        }
    }
}
