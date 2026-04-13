namespace ContactService.Domain.Contacts;

internal sealed record ContactAddressDto(
    string? Street,
    string? City,
    string? State,
    string? PostalCode,
    string? CountryOrRegion
);
