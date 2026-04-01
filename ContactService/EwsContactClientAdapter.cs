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
                BasePropertySet.FirstClassProperties,
                ItemSchema.Body,
                ContactSchema.JobTitle,
                ContactSchema.FileAs,
                ContactSchema.BusinessHomePage,
                ContactSchema.ImAddresses,
                ContactSchema.PhysicalAddresses,
                ContactSchema.PostalAddressIndex);

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
                var displayName = TryGetString(c, ContactSchema.DisplayName) ?? string.Empty;
                var givenName = TryGetString(c, ContactSchema.GivenName);
                var middleName = TryGetString(c, ContactSchema.MiddleName);
                var surname = TryGetString(c, ContactSchema.Surname);
                var companyName = TryGetString(c, ContactSchema.CompanyName);
                var jobTitle = TryGetString(c, ContactSchema.JobTitle);
                var fileAs = TryGetString(c, ContactSchema.FileAs);
                var businessHomePage = TryGetString(c, ContactSchema.BusinessHomePage);

                var emailDisplayNames = new Dictionary<string, string>();
                var emails = new Dictionary<string, string>();
                var emailDictionary = TryGetEmailAddresses(c);
                if (emailDictionary is not null)
                {
                    foreach (EmailAddressKey key in Enum.GetValues(typeof(EmailAddressKey)))
                    {
                        if (!emailDictionary.Contains(key))
                            continue;

                        var emailEntry = emailDictionary[key];
                        var address = emailEntry?.Address;
                        if (!string.IsNullOrWhiteSpace(address))
                            emails[key.ToString()] = address;

                        var emailDisplayName = emailEntry?.Name;
                        if (!string.IsNullOrWhiteSpace(emailDisplayName))
                            emailDisplayNames[key.ToString()] = emailDisplayName;
                    }
                }

                var imAddresses = new Dictionary<string, string>();
                var imAddressDictionary = TryGetImAddresses(c);
                if (imAddressDictionary is not null)
                {
                    foreach (ImAddressKey key in Enum.GetValues(typeof(ImAddressKey)))
                    {
                        if (!imAddressDictionary.Contains(key))
                            continue;

                        var imAddress = imAddressDictionary[key];
                        if (!string.IsNullOrWhiteSpace(imAddress))
                            imAddresses[key.ToString()] = imAddress;
                    }
                }

                var phoneNumbers = new Dictionary<string, string>();
                var phoneNumberDictionary = TryGetPhoneNumbers(c);
                if (phoneNumberDictionary is not null)
                {
                    foreach (PhoneNumberKey key in Enum.GetValues(typeof(PhoneNumberKey)))
                    {
                        if (!phoneNumberDictionary.Contains(key))
                            continue;

                        var number = phoneNumberDictionary[key];
                        if (!string.IsNullOrWhiteSpace(number))
                            phoneNumbers[key.ToString()] = number;
                    }
                }

                var addresses = new Dictionary<string, ContactAddressDto>();
                var physicalAddressDictionary = TryGetPhysicalAddresses(c);
                if (physicalAddressDictionary is not null)
                {
                    foreach (PhysicalAddressKey key in Enum.GetValues(typeof(PhysicalAddressKey)))
                    {
                        if (!physicalAddressDictionary.Contains(key))
                            continue;

                        var addressEntry = physicalAddressDictionary[key];
                        if (addressEntry is null)
                            continue;

                        var addressDto = new ContactAddressDto(
                            addressEntry.Street,
                            addressEntry.City,
                            addressEntry.State,
                            addressEntry.PostalCode,
                            addressEntry.CountryOrRegion);

                        var hasAddressData =
                            !string.IsNullOrWhiteSpace(addressDto.Street) ||
                            !string.IsNullOrWhiteSpace(addressDto.City) ||
                            !string.IsNullOrWhiteSpace(addressDto.State) ||
                            !string.IsNullOrWhiteSpace(addressDto.PostalCode) ||
                            !string.IsNullOrWhiteSpace(addressDto.CountryOrRegion);

                        if (hasAddressData)
                            addresses[key.ToString()] = addressDto;
                    }
                }

                emails.TryGetValue(EmailAddressKey.EmailAddress1.ToString(), out var email);
                if (string.IsNullOrWhiteSpace(email))
                    email = emails.Values.FirstOrDefault();

                phoneNumbers.TryGetValue(PhoneNumberKey.BusinessPhone.ToString(), out var businessPhone);
                phoneNumbers.TryGetValue(PhoneNumberKey.HomePhone.ToString(), out var homePhone);
                phoneNumbers.TryGetValue(PhoneNumberKey.BusinessFax.ToString(), out var businessFax);
                phoneNumbers.TryGetValue(PhoneNumberKey.MobilePhone.ToString(), out var mobile);

                var postalAddressKey = TryGetPostalAddressKey(c);
                var notes = TryGetBodyText(c);

                return new ContactDto(
                    c.Id?.UniqueId ?? string.Empty,
                    displayName,
                    givenName,
                    middleName,
                    surname,
                    companyName,
                    jobTitle,
                    fileAs,
                    businessHomePage,
                    emailDisplayNames,
                    emails,
                    imAddresses,
                    phoneNumbers,
                    addresses,
                    postalAddressKey,
                    email,
                    businessPhone,
                    homePhone,
                    businessFax,
                    mobile,
                    notes);
            }).ToList();

            int? nextOffset = result.MoreAvailable ? result.NextPageOffset : null;
            return System.Threading.Tasks.Task.FromResult(new ContactPageDto(mapped, nextOffset));
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException($"EWS contact read failed: {ex.Message}", ex);
        }
    }

    private static string? TryGetString(Contact contact, PropertyDefinitionBase property)
    {
        return contact.TryGetProperty(property, out string value) ? value : null;
    }

    private static EmailAddressDictionary? TryGetEmailAddresses(Contact contact)
    {
        return contact.TryGetProperty(ContactSchema.EmailAddresses, out EmailAddressDictionary value) ? value : null;
    }

    private static ImAddressDictionary? TryGetImAddresses(Contact contact)
    {
        return contact.TryGetProperty(ContactSchema.ImAddresses, out ImAddressDictionary value) ? value : null;
    }

    private static PhoneNumberDictionary? TryGetPhoneNumbers(Contact contact)
    {
        return contact.TryGetProperty(ContactSchema.PhoneNumbers, out PhoneNumberDictionary value) ? value : null;
    }

    private static PhysicalAddressDictionary? TryGetPhysicalAddresses(Contact contact)
    {
        return contact.TryGetProperty(ContactSchema.PhysicalAddresses, out PhysicalAddressDictionary value) ? value : null;
    }

    private static string? TryGetPostalAddressKey(Contact contact)
    {
        try
        {
            var key = contact.PostalAddressIndex.ToString();
            return string.IsNullOrWhiteSpace(key) ? null : key;
        }
        catch (ServiceObjectPropertyException)
        {
            return null;
        }
    }

    private static string? TryGetBodyText(Contact contact)
    {
        if (!contact.TryGetProperty(ItemSchema.Body, out MessageBody body))
            return null;

        return body.Text;
    }

    public void Dispose()
    {
        // ExchangeService has no IDisposable contract.
    }
}
