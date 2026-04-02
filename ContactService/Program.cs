using System.ComponentModel;

class Program
{
    static async Task Main(string[] args)
    {
        var accountKey = Environment.GetEnvironmentVariable("EWS_ACCOUNT_KEY") ?? "bewerbung";
        try
        {
            var provider = new EnvEwsConfigProvider();
            var factory = new EwsContactService();
            var engine = new ExchangeContactEngine(factory, provider, accountKey);

            var contacts = await engine.GetAllContactsAsync(pageSize: 100, CancellationToken.None);
            
            Console.WriteLine($"Loaded contacts: {contacts.Count}");
            foreach (var contact in contacts)
            {
                Console.WriteLine(contact.MobilePhone + " | " + contact.Company);
            }

            var dto = new ContactDto(
                Id: null, // oder ""
                DisplayName: "Max Mustermann2",
                GivenName: "Max2",
                MiddleName: null,
                Surname: "Mustermann",
                Company: null,
                JobTitle: null,
                FileAs: null,
                WebPage: null,
                EmailDisplayNames: new Dictionary<string, string>(),
                Emails: new Dictionary<string, string>{["EmailAddress1"] = "max@firma.de"},
                ImAddresses: new Dictionary<string, string>(),
                PhoneNumbers: new Dictionary<string, string>(),
                Addresses: new Dictionary<string, ContactAddressDto>(),
                PostalAddressKey: null,
                Email: null,
                BusinessPhone: "+49-12321-12321",
                HomePhone: null,
                BusinessFax: null,
                MobilePhone: null,
                Notes: "automatisch angelegt"
            );

            await engine.AddContactAsync(dto,CancellationToken.None);
            
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Contact sync failed.");
            Console.Error.WriteLine(ex.ToString());

            var inner = ex.InnerException;
            var depth = 1;
            while (inner is not null)
            {
                Console.Error.WriteLine($"Inner[{depth}] {inner.GetType().Name}: {inner.Message}");
                inner = inner.InnerException;
                depth++;
            }

            Environment.ExitCode = 1;
        }
    }
}
