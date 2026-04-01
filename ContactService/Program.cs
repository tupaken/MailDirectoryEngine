using System.Text.Json;

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
        Console.WriteLine(contact.MobilePhone+ " | "+contact.Company);
    }
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
