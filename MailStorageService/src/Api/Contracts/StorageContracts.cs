namespace MailStorageService.Api.Contracts;

/// <summary>
/// Represents a request to store an exported mail file for a case number.
/// </summary>
public sealed record StoreRequest(string SourcePath, string Number);

/// <summary>
/// Represents a simple message response from the storage service.
/// </summary>
public sealed record ServiceMessageResponse(string Message);

/// <summary>
/// Represents the health payload returned by the service.
/// </summary>
public sealed record HealthResponse(string Status);
