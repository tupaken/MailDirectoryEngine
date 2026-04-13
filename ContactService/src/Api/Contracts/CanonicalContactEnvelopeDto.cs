using System.Text.Json.Serialization;

namespace ContactService.Api.Contracts;

internal sealed record CanonicalContactEnvelopeDto(
    [property: JsonPropertyName("schema_version")] string SchemaVersion,
    [property: JsonPropertyName("contact")] CanonicalContactDto Contact,
    [property: JsonPropertyName("account_key")] string? AccountKey,
    [property: JsonPropertyName("source_message_id")] string? SourceMessageId
);
