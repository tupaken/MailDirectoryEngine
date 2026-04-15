using System.Text.Json.Serialization;

namespace ContactService.Api.Contracts;

/// <summary>
/// Represents the canonical contact payload exchanged between llmService and ContactService.
/// </summary>
/// <param name="FullName">Contact full name as extracted from the source message.</param>
/// <param name="GivenName">Optional given name component.</param>
/// <param name="Surname">Optional surname component.</param>
/// <param name="Company">Optional company or organization name.</param>
/// <param name="Email">Primary email address.</param>
/// <param name="Phones">Canonical phone numbers with display-oriented <c>raw</c> values and optional <c>e164</c> fallbacks.</param>
/// <param name="Address">Free-form postal address text.</param>
/// <param name="Website">Optional website URL.</param>
/// <param name="Notes">Optional free-form notes.</param>
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
