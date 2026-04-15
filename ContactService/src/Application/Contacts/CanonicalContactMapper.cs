using ContactService.Api.Contracts;
using ContactService.Domain.Contacts;

namespace ContactService.Application.Contacts;

internal static class CanonicalContactMapper
{
    /// <summary>
    /// Maps a canonical contact envelope to the internal contact DTO used by the EWS layer.
    /// </summary>
    /// <param name="payload">Canonical payload to map.</param>
    /// <returns>Mapped contact DTO with normalized names, display-oriented phones, and notes.</returns>
    public static ContactDto ToContactDto(CanonicalContactEnvelopeDto payload)
    {
        var contact = payload.Contact;

        var fullName = Clean(contact.FullName);
        var givenName = Clean(contact.GivenName);
        var surname = Clean(contact.Surname);

        if (string.IsNullOrWhiteSpace(fullName))
            fullName = BuildFullName(givenName, surname);

        if (string.IsNullOrWhiteSpace(givenName) || string.IsNullOrWhiteSpace(surname))
        {
            var (splitGivenName, splitSurname) = SplitName(fullName);
            if (string.IsNullOrWhiteSpace(givenName))
                givenName = splitGivenName;
            if (string.IsNullOrWhiteSpace(surname))
                surname = splitSurname;
        }

        var normalizedPhones = NormalizePhones(contact.Phones);
        var (businessPhone, mobilePhone, homePhone, businessFax, usedPhoneIndexes) =
            SelectPrimaryPhones(normalizedPhones);
        var additionalPhoneNumbers = BuildAdditionalPhoneNumbers(normalizedPhones, usedPhoneIndexes);

        var displayName = !string.IsNullOrWhiteSpace(fullName) ? fullName : BuildFullName(givenName, surname);
        if (string.IsNullOrWhiteSpace(displayName))
            displayName = Clean(contact.Email);
        if (string.IsNullOrWhiteSpace(displayName))
            displayName = businessPhone ?? mobilePhone ?? homePhone ?? businessFax ?? "Unknown Contact";

        var email = Clean(contact.Email);
        var emails = new Dictionary<string, string>();
        var emailDisplayNames = new Dictionary<string, string>();
        if (!string.IsNullOrWhiteSpace(email))
        {
            emails["EmailAddress1"] = email;
            emailDisplayNames["EmailAddress1"] = displayName;
        }

        var notes = BuildNotes(payload.SourceMessageId, contact.Address, contact.Notes);

        return new ContactDto(
            Id: null,
            DisplayName: displayName,
            GivenName: NullIfEmpty(givenName),
            MiddleName: null,
            Surname: NullIfEmpty(surname),
            Company: NullIfEmpty(Clean(contact.Company)),
            JobTitle: null,
            FileAs: displayName,
            WebPage: NullIfEmpty(Clean(contact.Website)),
            EmailDisplayNames: emailDisplayNames,
            Emails: emails,
            ImAddresses: new Dictionary<string, string>(),
            PhoneNumbers: additionalPhoneNumbers,
            Addresses: new Dictionary<string, ContactAddressDto>(),
            PostalAddressKey: null,
            Email: NullIfEmpty(email),
            BusinessPhone: NullIfEmpty(businessPhone),
            HomePhone: NullIfEmpty(homePhone),
            BusinessFax: NullIfEmpty(businessFax),
            MobilePhone: NullIfEmpty(mobilePhone),
            Notes: NullIfEmpty(notes));
    }

    private static string Clean(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim();
    }

    private static string? NullIfEmpty(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value;
    }

    private static string BuildFullName(string givenName, string surname)
    {
        var parts = new[] { Clean(givenName), Clean(surname) }.Where(part => part.Length > 0);
        return string.Join(" ", parts);
    }

    private static (string GivenName, string Surname) SplitName(string fullName)
    {
        var cleaned = Clean(fullName);
        if (string.IsNullOrWhiteSpace(cleaned))
            return (string.Empty, string.Empty);

        var parts = cleaned.Split(' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        if (parts.Length == 1)
            return (parts[0], string.Empty);

        var givenName = string.Join(" ", parts.Take(parts.Length - 1));
        var surname = parts[^1];
        return (givenName, surname);
    }

    private static string BuildNotes(string? sourceMessageId, string? address, string? notes)
    {
        var parts = new List<string>();
        var sourceId = Clean(sourceMessageId);
        if (!string.IsNullOrWhiteSpace(sourceId))
            parts.Add($"source_message_id={sourceId}");

        var cleanedAddress = Clean(address);
        if (!string.IsNullOrWhiteSpace(cleanedAddress))
            parts.Add($"address={cleanedAddress}");

        var cleanedNotes = Clean(notes);
        if (!string.IsNullOrWhiteSpace(cleanedNotes))
            parts.Add(cleanedNotes);

        return string.Join(Environment.NewLine, parts);
    }

    private static IReadOnlyList<NormalizedPhone> NormalizePhones(IReadOnlyList<CanonicalPhoneDto>? phones)
    {
        if (phones is null || phones.Count == 0)
            return Array.Empty<NormalizedPhone>();

        var normalized = new List<NormalizedPhone>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var phone in phones)
        {
            var value = PhoneValue(phone);
            if (string.IsNullOrWhiteSpace(value))
                continue;

            var dedupeKey = PhoneDigits(value);
            if (string.IsNullOrWhiteSpace(dedupeKey))
                dedupeKey = value;

            if (!seen.Add(dedupeKey))
                continue;

            normalized.Add(new NormalizedPhone(
                Type: NormalizePhoneType(phone.Type),
                Value: value));
        }

        return normalized;
    }

    private static (string? BusinessPhone, string? MobilePhone, string? HomePhone, string? BusinessFax, HashSet<int> UsedIndexes)
        SelectPrimaryPhones(IReadOnlyList<NormalizedPhone> phones)
    {
        var used = new HashSet<int>();

        var businessIndex = FindPhoneIndex(phones, "business");
        var mobileIndex = FindPhoneIndex(phones, "mobile");
        var homeIndex = FindPhoneIndex(phones, "home");
        var faxIndex = FindPhoneIndex(phones, "fax");

        string? businessPhone = null;
        if (businessIndex >= 0)
        {
            businessPhone = phones[businessIndex].Value;
            used.Add(businessIndex);
        }

        if (string.IsNullOrWhiteSpace(businessPhone) && phones.Count > 0)
        {
            businessPhone = phones[0].Value;
            used.Add(0);
        }

        string? mobilePhone = null;
        if (mobileIndex >= 0)
        {
            mobilePhone = phones[mobileIndex].Value;
            used.Add(mobileIndex);
        }

        string? homePhone = null;
        if (homeIndex >= 0)
        {
            homePhone = phones[homeIndex].Value;
            used.Add(homeIndex);
        }

        string? businessFax = null;
        if (faxIndex >= 0)
        {
            businessFax = phones[faxIndex].Value;
            used.Add(faxIndex);
        }

        return (businessPhone, mobilePhone, homePhone, businessFax, used);
    }

    private static IReadOnlyDictionary<string, string> BuildAdditionalPhoneNumbers(
        IReadOnlyList<NormalizedPhone> phones,
        HashSet<int> usedPhoneIndexes)
    {
        var mapped = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var usedValues = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var index in usedPhoneIndexes)
        {
            if (index >= 0 && index < phones.Count)
                usedValues.Add(phones[index].Value);
        }

        AddByType(phones, usedPhoneIndexes, usedValues, mapped, "business", "BusinessPhone2");
        AddByType(phones, usedPhoneIndexes, usedValues, mapped, "home", "HomePhone2");

        var fallbackKeys = new Queue<string>(new[]
        {
            "CompanyMainPhone",
            "OtherTelephone",
            "PrimaryPhone",
            "AssistantPhone",
            "Callback",
            "CarPhone",
            "Pager",
            "RadioPhone",
            "Telex",
            "TtyTddPhone",
            "Isdn"
        });

        for (var index = 0; index < phones.Count; index++)
        {
            if (usedPhoneIndexes.Contains(index))
                continue;

            var value = phones[index].Value;
            if (string.IsNullOrWhiteSpace(value) || usedValues.Contains(value))
                continue;

            while (fallbackKeys.Count > 0 && mapped.ContainsKey(fallbackKeys.Peek()))
            {
                fallbackKeys.Dequeue();
            }

            if (fallbackKeys.Count == 0)
                break;

            var key = fallbackKeys.Dequeue();
            mapped[key] = value;
            usedValues.Add(value);
            usedPhoneIndexes.Add(index);
        }

        return mapped;
    }

    private static void AddByType(
        IReadOnlyList<NormalizedPhone> phones,
        HashSet<int> usedPhoneIndexes,
        HashSet<string> usedValues,
        IDictionary<string, string> mapped,
        string phoneType,
        string ewsKey)
    {
        if (mapped.ContainsKey(ewsKey))
            return;

        for (var index = 0; index < phones.Count; index++)
        {
            if (usedPhoneIndexes.Contains(index))
                continue;

            var phone = phones[index];
            if (!string.Equals(phone.Type, phoneType, StringComparison.OrdinalIgnoreCase))
                continue;
            if (usedValues.Contains(phone.Value))
                continue;

            mapped[ewsKey] = phone.Value;
            usedValues.Add(phone.Value);
            usedPhoneIndexes.Add(index);
            return;
        }
    }

    private static int FindPhoneIndex(IReadOnlyList<NormalizedPhone> phones, string type)
    {
        for (var index = 0; index < phones.Count; index++)
        {
            if (string.Equals(phones[index].Type, type, StringComparison.OrdinalIgnoreCase))
                return index;
        }

        return -1;
    }

    private static string NormalizePhoneType(string? type)
    {
        var cleaned = Clean(type).ToLowerInvariant();
        if (cleaned.Length == 0)
            return "other";

        if (cleaned.Contains("fax"))
            return "fax";
        if (cleaned.Contains("mobil") || cleaned.Contains("mobile") || cleaned.Contains("handy") || cleaned.Contains("cell"))
            return "mobile";
        if (cleaned.Contains("home") || cleaned.Contains("privat") || cleaned.Contains("private"))
            return "home";
        if (
            cleaned.Contains("business") ||
            cleaned.Contains("office") ||
            cleaned.Contains("work") ||
            cleaned.Contains("telefon") ||
            cleaned.Contains("phone") ||
            cleaned.Contains("tel")
        )
        {
            return "business";
        }

        return "other";
    }

    private static string PhoneValue(CanonicalPhoneDto phone)
    {
        // Prefer the human-readable raw value now that llmService normalizes it to the shared display format.
        var raw = Clean(phone.Raw);
        if (!string.IsNullOrWhiteSpace(raw))
            return raw;

        var e164 = Clean(phone.E164);
        if (!string.IsNullOrWhiteSpace(e164))
            return e164;

        return string.Empty;
    }

    private static string PhoneDigits(string value)
    {
        return string.Concat(value.Where(char.IsDigit));
    }

    private sealed record NormalizedPhone(string Type, string Value);
}
