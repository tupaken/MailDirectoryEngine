namespace ContactService.Domain.Contacts;

internal sealed record ContactPageDto(
    IReadOnlyList<ContactDto> Items,
    int? NextOffset
);
