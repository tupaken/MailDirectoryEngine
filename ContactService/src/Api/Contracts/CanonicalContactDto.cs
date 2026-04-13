using System.Text.Json.Serialization;

namespace ContactService.Api.Contracts;

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
