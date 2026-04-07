using System.Text.Json.Serialization;

internal static class CanonicalContactSchema
{
    public const string Version = "1.0";
}

internal sealed record CanonicalContactEnvelopeDto(
    [property: JsonPropertyName("schema_version")] string SchemaVersion,
    [property: JsonPropertyName("contact")] CanonicalContactDto Contact,
    [property: JsonPropertyName("account_key")] string? AccountKey,
    [property: JsonPropertyName("source_message_id")] string? SourceMessageId
);

internal sealed record CanonicalContactDto(
    [property: JsonPropertyName("full_name")] string? FullName,
    [property: JsonPropertyName("given_name")] string? GivenName,
    [property: JsonPropertyName("surname")] string? Surname,
    [property: JsonPropertyName("company")] string? Company,
    [property: JsonPropertyName("email")] string? Email,
    [property: JsonPropertyName("phones")] IReadOnlyList<CanonicalPhoneDto>? Phones,
    [property: JsonPropertyName("address")] string? Address,
    [property: JsonPropertyName("website")] string? Website,
    [property: JsonPropertyName("notes")] string? Notes
);

internal sealed record CanonicalPhoneDto(
    [property: JsonPropertyName("type")] string? Type,
    [property: JsonPropertyName("raw")] string? Raw,
    [property: JsonPropertyName("e164")] string? E164
);
