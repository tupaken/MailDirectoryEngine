using System.Text.Json.Serialization;

namespace ContactService.Api.Contracts;

/// <summary>
/// Wraps one canonical contact together with schema and routing metadata.
/// </summary>
/// <param name="SchemaVersion">Canonical payload schema version expected by ContactService.</param>
/// <param name="Contact">Canonical contact body to map and persist.</param>
/// <param name="AccountKey">Optional tenant or mailbox key associated with the source message.</param>
/// <param name="SourceMessageId">Optional upstream message identifier used for traceability.</param>
internal sealed record CanonicalContactEnvelopeDto(
    [property: JsonPropertyName("schema_version")] string SchemaVersion,
    [property: JsonPropertyName("contact")] CanonicalContactDto Contact,
    [property: JsonPropertyName("account_key")] string? AccountKey,
    [property: JsonPropertyName("source_message_id")] string? SourceMessageId
);
