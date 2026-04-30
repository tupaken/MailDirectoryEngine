namespace MailStorageService.Api.Contracts;

/// <summary>
/// Represents a request to store an exported mail file for a case number.
/// </summary>
/// <param name="SourcePath">Container-visible source path to the exported mail file.</param>
/// <param name="Number">Case number used to resolve the destination directory.</param>
/// <param name="TargetFileName">Destination file name without extension or path segments.</param>
public sealed record StoreRequest(string SourcePath, string Number, string TargetFileName);

/// <summary>
/// Represents a simple message response from the storage service.
/// </summary>
public sealed record ServiceMessageResponse(string Message);

/// <summary>
/// Represents the health payload returned by the service.
/// </summary>
public sealed record HealthResponse(string Status);
