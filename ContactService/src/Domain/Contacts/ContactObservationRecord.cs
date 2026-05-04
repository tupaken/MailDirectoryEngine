namespace ContactService.Domain.Contacts;

internal sealed record ContactObservationRecord(
    long Id,
    string AccountKey,
    string IdentityKey,
    string? SourceMessageId,
    string? FullName,
    string? Company,
    string? Email,
    string? NormalizedEmail,
    string PhoneType,
    string PhoneRaw,
    string PhoneDigits,
    string EvidenceJson,
    string PayloadJson,
    string Status,
    string? Reason,
    int SeenCount,
    string? PromotedContactEwsId
);

internal sealed record ContactWriteResult(
    string Status,
    string? EwsId,
    IReadOnlyList<ContactFieldChange>? Changes = null
);

internal sealed record ExistingContactIdentity(
    long Id,
    string EwsId,
    string DisplayName,
    string? FullName,
    string? Company,
    string? NormalizedEmail
);

internal sealed record ContactFieldChange(
    string FieldName,
    string? OldValue,
    string? NewValue
);
