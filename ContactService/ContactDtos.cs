internal sealed record ContactDto(
    string Id,
    string DisplayName,
    string? GivenName,
    string? Surname,
    string? Email,
    string? Company,
    string? MobilePhone
);

internal sealed record ContactPageDto(
    IReadOnlyList<ContactDto> Items,
    int? NextOffset
);
