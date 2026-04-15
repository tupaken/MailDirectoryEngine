namespace ContactService.Api.Contracts;

/// <summary>
/// Describes the outcome returned after ContactService processes one canonical contact payload.
/// </summary>
/// <param name="Status">High-level sync result such as <c>created</c> or <c>duplicate</c>.</param>
/// <param name="AccountKey">Account or mailbox key associated with the sync operation.</param>
/// <param name="DisplayName">Display name of the affected contact.</param>
/// <param name="Email">Primary email that participated in matching or creation.</param>
/// <param name="Phone">Primary phone value returned to the caller.</param>
internal sealed record ContactSyncResultDto(
    string Status,
    string AccountKey,
    string DisplayName,
    string? Email,
    string? Phone
);
