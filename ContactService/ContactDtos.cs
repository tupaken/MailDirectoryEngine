internal sealed record ContactAddressDto(
    string? Street,
    string? City,
    string? State,
    string? PostalCode,
    string? CountryOrRegion
);

internal sealed record ContactDto(
    string? Id,
    string DisplayName,
    string? GivenName,
    string? MiddleName,
    string? Surname,
    string? Company,
    string? JobTitle,
    string? FileAs,
    string? WebPage,
    IReadOnlyDictionary<string, string> EmailDisplayNames,
    IReadOnlyDictionary<string, string> Emails,
    IReadOnlyDictionary<string, string> ImAddresses,
    IReadOnlyDictionary<string, string> PhoneNumbers,
    IReadOnlyDictionary<string, ContactAddressDto> Addresses,
    string? PostalAddressKey,
    string? Email,
    string? BusinessPhone,
    string? HomePhone,
    string? BusinessFax,
    string? MobilePhone,
    string? Notes
)
{
    public ContactDto(string DisplayName, string Email)
    {
        this.DisplayName = DisplayName;
        this.Email = Email;
    }
}

internal sealed record ContactPageDto(
    IReadOnlyList<ContactDto> Items,
    int? NextOffset
);
