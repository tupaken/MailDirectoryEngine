using System;
using MailKit;
using MailKit.Net.Imap;
using MailKit.Security;
using MimeKit;

namespace test{

    class TEST
    {
        static void Main(string[] args)
        {
            using (var client = new ImapClient())
            {
                client.Connect("adresse", 993, SecureSocketOptions.SslOnConnect);

                client.Authenticate("e-mail", "password");

                var ns = client.PersonalNamespaces[0];
                var root = client.GetFolder(ns);

                var folders = root.GetSubfolders(true).ToList();

                var sent = folders.FirstOrDefault(f =>
                            string.Equals(f.Name, "Gesendete Elemente", StringComparison.Ordinal) ||
                            string.Equals(f.FullName, "Gesendete Elemente", StringComparison.Ordinal) ||
                            f.FullName.EndsWith($"{ns.DirectorySeparator}Gesendete Elemente", StringComparison.Ordinal) ||
                            f.FullName.EndsWith($".Gesendete Elemente", StringComparison.Ordinal));

                sent.Open(FolderAccess.ReadOnly);

                Console.WriteLine($"Gefunden: {sent.FullName} | Count: {sent.Count}");

                var inbox = client.Inbox;
                inbox.Open(FolderAccess.ReadOnly);
                MimeMessage latest = inbox.GetMessage(inbox.Count - 1);
                Console.WriteLine("\nNEUESTE MAIL:");
                Console.WriteLine($"From: {latest.From}");
                Console.WriteLine($"Subject: {latest.Subject}");
                Console.WriteLine($"Date: {latest.Date}");

                client.Disconnect(true);
            }
        }
    }
}   
