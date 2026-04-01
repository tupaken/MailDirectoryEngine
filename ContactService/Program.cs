var accountKey = Environment.GetEnvironmentVariable("EWS_ACCOUNT_KEY") ?? "bewerbung";

try
{
    var provider = new EnvEwsConfigProvider();
    var factory = new EwsContactService();
    var engine = new ExchangeContactEngine(factory, provider, accountKey);

    var contacts = await engine.GetAllContactsAsync(pageSize: 100, CancellationToken.None);

    Console.WriteLine($"Loaded contacts: {contacts.Count}");
    foreach (var contact in contacts.Take(10))
    {
        Console.WriteLine($"{contact.DisplayName} | {contact.Email}");
    }
}
catch (Exception ex)
{
    Console.Error.WriteLine($"Contact sync failed: {ex.Message}");
    Environment.ExitCode = 1;
}
