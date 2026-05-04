

using ContactService.Domain.Contacts;

namespace ContactService.Domain.Abstractions;

internal interface IContactStore
{
    Task<string?> ExistsAsync(ContactDto dto, CancellationToken ct);
    Task<long> InsertAsync(ContactDto dto,string ewsId, string? sourceMessageId, CancellationToken ct);
    Task<long?> FindContactIdByEwsIdAsync(string ewsId, CancellationToken ct);
    Task UpdateFromPromotedObservationAsync(ContactDto dto, string ewsId, string? sourceMessageId, CancellationToken ct);
    Task<ContactObservationRecord> UpsertObservationAsync(ContactObservationRecord observation, CancellationToken ct);
    Task MarkObservationStatusAsync(long observationId, string status, string? reason, string? promotedContactEwsId, CancellationToken ct);
    Task<int> CountDistinctNamesForPhoneAsync(string phoneDigits, string? fullName, CancellationToken ct);
    Task<int> CountDistinctNamesForEmailAsync(string normalizedEmail, string? fullName, CancellationToken ct);
    Task<ExistingContactIdentity?> FindExistingContactByEmailAsync(string normalizedEmail, CancellationToken ct);
    Task<int> CountExistingContactsForPhoneAsync(string phoneDigits, string? normalizedEmail, CancellationToken ct);
    Task InsertChangeLogAsync(
        long? contactId,
        string? ewsId,
        long? observationId,
        string action,
        string? fieldName,
        string? oldValue,
        string? newValue,
        string? sourceMessageId,
        string? reason,
        CancellationToken ct);
}
