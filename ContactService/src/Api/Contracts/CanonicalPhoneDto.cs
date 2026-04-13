using System.Text.Json.Serialization;

namespace ContactService.Api.Contracts;

internal sealed record CanonicalPhoneDto(
    [property: JsonPropertyName("type")] string? Type,
    [property: JsonPropertyName("raw")] string? Raw,
    [property: JsonPropertyName("e164")] string? E164
);
