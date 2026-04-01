using Microsoft.Exchange.WebServices.Data;

internal sealed class EwsContactClientAdapter : IEwsContactClient
{
    private readonly ExchangeService _service;

    public EwsContactClientAdapter(ExchangeService service)
    {
        _service = service ?? throw new ArgumentNullException(nameof(service));
    }

    public Task<ContactPageDto> GetContactsPageAsync(int offset, int pageSize, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();

        if (offset < 0)
            throw new ArgumentOutOfRangeException(nameof(offset));

        if (pageSize <= 0)
            throw new ArgumentOutOfRangeException(nameof(pageSize));

        try
        {
            var detailPropertySet = new PropertySet(
                BasePropertySet.IdOnly,
                ContactSchema.DisplayName,
                ContactSchema.GivenName,
                ContactSchema.Surname,
                ContactSchema.CompanyName,
                ContactSchema.EmailAddresses,
                ContactSchema.PhoneNumbers);

            var view = new ItemView(pageSize, offset, OffsetBasePoint.Beginning)
            {
                PropertySet = new PropertySet(BasePropertySet.IdOnly)
            };

            var result = _service.FindItems(WellKnownFolderName.Contacts, view);

            var contacts = result.Items.OfType<Contact>().ToList();
            if (contacts.Count > 0)
                _service.LoadPropertiesForItems(contacts, detailPropertySet);

            var mapped = contacts.Select(c =>
            {
                var email = c.EmailAddresses.Contains(EmailAddressKey.EmailAddress1)
                    ? c.EmailAddresses[EmailAddressKey.EmailAddress1].Address
                    : null;

                var mobile = c.PhoneNumbers.Contains(PhoneNumberKey.MobilePhone)
                    ? c.PhoneNumbers[PhoneNumberKey.MobilePhone]
                    : null;

                return new ContactDto(
                    c.Id?.UniqueId ?? string.Empty,
                    c.DisplayName ?? string.Empty,
                    c.GivenName,
                    c.Surname,
                    email,
                    c.CompanyName,
                    mobile);
            }).ToList();

            int? nextOffset = result.MoreAvailable ? result.NextPageOffset : null;
            return System.Threading.Tasks.Task.FromResult(new ContactPageDto(mapped, nextOffset));
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException("EWS contact read failed.", ex);
        }
    }

    public void Dispose()
    {
        // ExchangeService has no IDisposable contract.
    }
}
