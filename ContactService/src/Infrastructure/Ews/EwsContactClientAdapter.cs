using ContactService.Domain.Abstractions;
using ContactService.Domain.Contacts;
using Microsoft.Exchange.WebServices.Data;
namespace ContactService.Infrastructure.Ews;

internal sealed class EwsContactClientAdapter : IEwsContactClient
{
    private readonly ExchangeService _service;
    private readonly IContactStore _contactStore;
    private readonly Func<ContactDto, CancellationToken, System.Threading.Tasks.Task<string>> _saveContactAsync;
    private readonly Func<string, System.Threading.Tasks.Task> _deleteContactAsync;

    public EwsContactClientAdapter(ExchangeService service, IContactStore contactStore)
        : this(service, contactStore, saveContactAsync: null, deleteContactAsync: null)
    {
    }

    internal EwsContactClientAdapter(
        ExchangeService service,
        IContactStore contactStore,
        Func<ContactDto, CancellationToken, System.Threading.Tasks.Task<string>>? saveContactAsync,
        Func<string, System.Threading.Tasks.Task>? deleteContactAsync)
    {
        _service = service ?? throw new ArgumentNullException(nameof(service));
        _contactStore = contactStore ?? throw new ArgumentNullException(nameof(contactStore));
        _saveContactAsync = saveContactAsync ?? SaveContactAsync;
        _deleteContactAsync = deleteContactAsync ?? DeleteContactAsync;
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

    public async System.Threading.Tasks.Task AddContactAsync(
        ContactDto dto,
        CancellationToken ct,
        string? sourceMessageId = null,
        long? observationId = null)
    {
        await UpsertContactAsync(dto, ct, sourceMessageId, observationId).ConfigureAwait(false);
    }

    public async System.Threading.Tasks.Task<ContactWriteResult> UpsertContactAsync(
        ContactDto dto,
        CancellationToken ct,
        string? sourceMessageId = null,
        long? observationId = null)
    {
        if (dto is null)
            throw new ArgumentNullException(nameof(dto));

        string? ex = await _contactStore.ExistsAsync(dto, ct);

        if (ex!=null)
        {
            var changes = await UpdateExistingContactFieldsAsync(ex, dto, ct).ConfigureAwait(false);
            if (changes.Count > 0)
            {
                await _contactStore.UpdateFromPromotedObservationAsync(dto, ex, sourceMessageId, ct).ConfigureAwait(false);

                var contactId = await _contactStore.FindContactIdByEwsIdAsync(ex, ct).ConfigureAwait(false);
                foreach (var change in changes)
                {
                    await _contactStore.InsertChangeLogAsync(
                        contactId,
                        ex,
                        observationId,
                        "updated",
                        change.FieldName,
                        change.OldValue,
                        change.NewValue,
                        sourceMessageId,
                        "promoted_observation_changed_field",
                        ct).ConfigureAwait(false);
                }
            }
            else
            {
                var contactId = await _contactStore.FindContactIdByEwsIdAsync(ex, ct).ConfigureAwait(false);
                await _contactStore.InsertChangeLogAsync(
                    contactId,
                    ex,
                    observationId,
                    "unchanged",
                    null,
                    null,
                    dto.DisplayName,
                    sourceMessageId,
                    "promoted_observation_no_field_change",
                    ct).ConfigureAwait(false);
            }

            return new ContactWriteResult(changes.Count > 0 ? "updated" : "unchanged", ex, changes);
        }

        var ewsItemId = await _saveContactAsync(dto, ct).ConfigureAwait(false);

        try
        {
            var contactId = await _contactStore.InsertAsync(dto, ewsItemId, sourceMessageId, ct).ConfigureAwait(false);
            await _contactStore.InsertChangeLogAsync(
                contactId,
                ewsItemId,
                observationId,
                "created",
                null,
                null,
                dto.DisplayName,
                sourceMessageId,
                "promoted_observation_created_contact",
                ct).ConfigureAwait(false);
        }
        catch (Exception ex2)
        {
            try
            {
                await _deleteContactAsync(ewsItemId).ConfigureAwait(false);
            }
            catch (Exception rollbackEx)
            {
                throw new InvalidOperationException(
                    $"Persisting contact metadata failed after saving Exchange contact '{ewsItemId}', and rollback delete failed.",
                    new AggregateException(ex2, rollbackEx));
            }

            throw;
        }

        return new ContactWriteResult("created", ewsItemId);
    }

    private async System.Threading.Tasks.Task<string> SaveContactAsync(ContactDto dto, CancellationToken ct)
    {
        var contact = new Contact(_service);
        MapToEwsContact(contact, dto);

        await System.Threading.Tasks.Task.Run(() =>
        {
            ct.ThrowIfCancellationRequested();
            contact.Save(WellKnownFolderName.Contacts);
        }, ct).ConfigureAwait(false);

        return contact.Id?.UniqueId
            ?? throw new InvalidOperationException("Exchange contact was saved without an item id.");
    }

    private System.Threading.Tasks.Task DeleteContactAsync(string ewsItemId)
    {
        return System.Threading.Tasks.Task.Run(() =>
        {
            var savedContact = Contact.Bind(_service, new ItemId(ewsItemId));
            savedContact.Delete(DeleteMode.HardDelete);
        });
    }

    private async System.Threading.Tasks.Task<IReadOnlyList<ContactFieldChange>> UpdateExistingContactFieldsAsync(
        string ewsItemId,
        ContactDto dto,
        CancellationToken ct)
    {
        return await System.Threading.Tasks.Task.Run(() =>
        {
            ct.ThrowIfCancellationRequested();

            var contact = Contact.Bind(_service, new ItemId(ewsItemId), new PropertySet(
                BasePropertySet.FirstClassProperties,
                ContactSchema.EmailAddresses,
                ContactSchema.PhoneNumbers,
                ContactSchema.BusinessHomePage));

            var changes = new List<ContactFieldChange>();
            AddIfChanged(changes, "given_name", contact.GivenName, dto.GivenName, value => contact.GivenName = value, overwrite: false);
            AddIfChanged(changes, "surname", contact.Surname, dto.Surname, value => contact.Surname = value, overwrite: false);
            AddIfChanged(changes, "company_name", contact.CompanyName, dto.Company, value => contact.CompanyName = value, overwrite: false);
            AddIfChanged(changes, "website", contact.BusinessHomePage, dto.WebPage, value => contact.BusinessHomePage = value, overwrite: false);
            AddEmailIfMissing(changes, contact, EmailAddressKey.EmailAddress1, dto.Email, dto.DisplayName);
            AddPhoneIfChanged(changes, contact, PhoneNumberKey.BusinessPhone, dto.BusinessPhone);
            AddPhoneIfChanged(changes, contact, PhoneNumberKey.HomePhone, dto.HomePhone);
            AddPhoneIfChanged(changes, contact, PhoneNumberKey.MobilePhone, dto.MobilePhone);
            AddPhoneIfChanged(changes, contact, PhoneNumberKey.BusinessFax, dto.BusinessFax);

            if (dto.PhoneNumbers is not null)
            {
                foreach (var kv in dto.PhoneNumbers)
                {
                    if (!Enum.TryParse<PhoneNumberKey>(kv.Key, ignoreCase: true, out var key))
                        continue;

                    AddPhoneIfChanged(changes, contact, key, kv.Value);
                }
            }

            if (changes.Count > 0)
                contact.Update(ConflictResolutionMode.AutoResolve);

            return changes;
        }, ct).ConfigureAwait(false);
    }

    private static void MapToEwsContact(Contact contact, ContactDto dto)
    {
        contact.DisplayName = dto.DisplayName;
        contact.GivenName = dto.GivenName;
        contact.MiddleName = dto.MiddleName;
        contact.Surname = dto.Surname;
        contact.CompanyName = dto.Company;
        contact.JobTitle = dto.JobTitle;
        contact.FileAs = dto.FileAs;
        contact.BusinessHomePage = dto.WebPage;

        if (!string.IsNullOrWhiteSpace(dto.Notes))
            contact.Body = "Automatisch angelegt \n" + dto.Notes;

        MapEmails(contact, dto);
        MapPhones(contact, dto);
        MapAddresses(contact, dto);
    }

    private static void MapEmails(Contact contact, ContactDto dto)
    {
        if (dto.Emails is null)
            return;

        foreach (var kv in dto.Emails)
        {
            if (string.IsNullOrWhiteSpace(kv.Value))
                continue;

            if (Enum.TryParse<EmailAddressKey>(kv.Key, ignoreCase: true, out var key))
                contact.EmailAddresses[key] = kv.Value;
        }
    }

    private static void MapPhones(Contact contact, ContactDto dto)
    {
        if (dto.PhoneNumbers is not null)
        {
            foreach (var kv in dto.PhoneNumbers)
            {
                if (string.IsNullOrWhiteSpace(kv.Value))
                    continue;

                if (Enum.TryParse<PhoneNumberKey>(kv.Key, ignoreCase: true, out var key))
                    contact.PhoneNumbers[key] = kv.Value;
            }
        }

        SetPhoneIfPresent(contact, PhoneNumberKey.BusinessPhone, dto.BusinessPhone);
        SetPhoneIfPresent(contact, PhoneNumberKey.HomePhone, dto.HomePhone);
        SetPhoneIfPresent(contact, PhoneNumberKey.MobilePhone, dto.MobilePhone);
        SetPhoneIfPresent(contact, PhoneNumberKey.BusinessFax, dto.BusinessFax);
    }

    private static void SetPhoneIfPresent(Contact contact, PhoneNumberKey key, string? value)
    {
        if (!string.IsNullOrWhiteSpace(value))
            contact.PhoneNumbers[key] = value;
    }

    private static void AddPhoneIfChanged(
        ICollection<ContactFieldChange> changes,
        Contact contact,
        PhoneNumberKey key,
        string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return;

        var oldValue = contact.PhoneNumbers.Contains(key) ? contact.PhoneNumbers[key] : null;
        if (PhoneDigits(oldValue) == PhoneDigits(value))
            return;

        contact.PhoneNumbers[key] = value;
        changes.Add(new ContactFieldChange(key.ToString(), oldValue, value));
    }

    private static void AddEmailIfMissing(
        ICollection<ContactFieldChange> changes,
        Contact contact,
        EmailAddressKey key,
        string? value,
        string displayName)
    {
        if (string.IsNullOrWhiteSpace(value))
            return;

        if (contact.EmailAddresses.Contains(key) &&
            !string.IsNullOrWhiteSpace(contact.EmailAddresses[key]?.Address))
        {
            return;
        }

        contact.EmailAddresses[key] = new EmailAddress(displayName, value);
        changes.Add(new ContactFieldChange(key.ToString(), null, value));
    }

    private static void AddIfChanged(
        ICollection<ContactFieldChange> changes,
        string fieldName,
        string? oldValue,
        string? newValue,
        Action<string> setValue,
        bool overwrite)
    {
        if (string.IsNullOrWhiteSpace(newValue))
            return;

        if (!string.IsNullOrWhiteSpace(oldValue) && !overwrite)
            return;

        if (string.Equals(oldValue?.Trim(), newValue.Trim(), StringComparison.Ordinal))
            return;

        setValue(newValue);
        changes.Add(new ContactFieldChange(fieldName, oldValue, newValue));
    }

    private static string PhoneDigits(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return string.Empty;

        return string.Concat(value.Where(char.IsDigit));
    }

    private static void MapAddresses(Contact contact, ContactDto dto)
    {
        if (dto.Addresses is null)
            return;

        foreach (var kv in dto.Addresses)
        {
            if (!Enum.TryParse<PhysicalAddressKey>(kv.Key, ignoreCase: true, out var key))
                continue;

            var address = kv.Value;
            contact.PhysicalAddresses[key] = new PhysicalAddressEntry
            {
                Street = address.Street,
                City = address.City,
                State = address.State,
                PostalCode = address.PostalCode,
                CountryOrRegion = address.CountryOrRegion
            };
        }

        if (!string.IsNullOrWhiteSpace(dto.PostalAddressKey) &&
            Enum.TryParse<PhysicalAddressIndex>(dto.PostalAddressKey, ignoreCase: true, out var postalIndex))
        {
            contact.PostalAddressIndex = postalIndex;
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
