using MailStorageService.Api.Contracts;
using MailStorageService.Storage;
using Microsoft.AspNetCore.Http.HttpResults;

namespace MailStorageService.Api.Endpoints;

/// <summary>
/// Maps HTTP endpoints for the mail storage service.
/// </summary>
internal static class StorageEndpoints
{
    /// <summary>
    /// Registers all storage-related endpoints on the application.
    /// </summary>
    /// <param name="app">The endpoint route builder.</param>
    public static void MapStorageEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/health", Health);
        app.MapPost("/store", Store);
    }

    /// <summary>
    /// Returns a basic health response for readiness checks.
    /// </summary>
    /// <returns>An <c>ok</c> health payload.</returns>
    internal static Ok<HealthResponse> Health()
    {
        return TypedResults.Ok(new HealthResponse("ok"));
    }

    /// <summary>
    /// Stores an exported mail file in the resolved target directory.
    /// </summary>
    /// <param name="request">The request payload containing source path and case number.</param>
    /// <param name="storageEngine">The storage engine used to resolve and copy the file.</param>
    /// <returns>
    /// An HTTP 200 response when the file was stored successfully; otherwise an HTTP 400 response.
    /// </returns>
    internal static Results<Ok<ServiceMessageResponse>, BadRequest<ServiceMessageResponse>> Store(
        StoreRequest request,
        IStorageEngine storageEngine)
    {
        var success = storageEngine.Store(request.SourcePath, request.Number);

        return success
            ? TypedResults.Ok(new ServiceMessageResponse("200"))
            : TypedResults.BadRequest(new ServiceMessageResponse("400"));
    }
}
