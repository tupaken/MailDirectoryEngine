namespace ContactService.Api.Contracts;

/// <summary>
/// Describes the outcome after a canonical contact candidate was quarantined and optionally promoted.
/// </summary>
internal sealed record ContactObservationResultDto(
    string Status,
    string AccountKey,
    long ObservationId,
    int SeenCount,
    string? Reason,
    string DisplayName,
    string? Email,
    string? Phone,
    string? ExchangeStatus
);
