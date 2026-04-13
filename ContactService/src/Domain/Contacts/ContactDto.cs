namespace ContactService.Domain.Contacts;

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
);
