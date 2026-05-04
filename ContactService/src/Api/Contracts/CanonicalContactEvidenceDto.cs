using System.Text.Json.Serialization;

namespace ContactService.Api.Contracts;

/// <summary>
/// Deterministic evidence flags computed before ContactService decides whether an LLM contact may be promoted.
/// </summary>
internal sealed record CanonicalContactEvidenceDto(
    [property: JsonPropertyName("source_kind")] string? SourceKind,
    [property: JsonPropertyName("email_in_source_block")] bool EmailInSourceBlock,
    [property: JsonPropertyName("phone_in_source_block")] bool PhoneInSourceBlock,
    [property: JsonPropertyName("name_in_source_block")] bool NameInSourceBlock,
    [property: JsonPropertyName("company_in_source_block")] bool CompanyInSourceBlock
);
