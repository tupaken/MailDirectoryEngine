using System.Text.Json.Serialization;

namespace ContactService.Api.Contracts;

/// <summary>
/// Represents one canonical phone number in display and machine-readable form.
/// </summary>
/// <param name="Type">Canonical phone category such as <c>business</c>, <c>mobile</c>, <c>home</c>, or <c>fax</c>.</param>
/// <param name="Raw">Human-readable phone text. German numbers are expected as <c>+49 XXX REST</c>.</param>
/// <param name="E164">Machine-readable international value without display spacing when available.</param>
internal sealed record CanonicalPhoneDto(
    [property: JsonPropertyName("type")] string? Type,
    [property: JsonPropertyName("raw")] string? Raw,
    [property: JsonPropertyName("e164")] string? E164
);
