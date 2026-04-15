namespace ContactService.Api.Contracts;

/// <summary>
/// Defines the canonical contact payload schema version supported by ContactService.
/// </summary>
internal static class CanonicalContactSchema
{
    /// <summary>
    /// Current canonical schema version shared between llmService and ContactService.
    /// </summary>
    public const string Version = "1.0";
}
