namespace ContactService.Api.Contracts;

internal sealed record ContactSyncResultDto(
    string Status,
    string AccountKey,
    string DisplayName,
    string? Email,
    string? Phone
);
