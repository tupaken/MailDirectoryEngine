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
    /// An HTTP 200 response when the file was stored successfully; otherwise a structured
    /// 400/404/503/500 response describing the failure reason.
    /// </returns>
    internal static Results<
        Ok<ServiceMessageResponse>,
        NotFound<ServiceMessageResponse>,
        BadRequest<ServiceMessageResponse>,
        JsonHttpResult<ServiceMessageResponse>> Store(
        StoreRequest request,
        IStorageEngine storageEngine)
    {
        var status = storageEngine.Store(request.SourcePath, request.Number, request.TargetFileName);

        return status switch
        {
            StoreStatus.Success => TypedResults.Ok(new ServiceMessageResponse("200")),
            StoreStatus.DestinationNotFound => TypedResults.NotFound(
                new ServiceMessageResponse("destination_not_found")),
            StoreStatus.SourceNotFound => TypedResults.NotFound(
                new ServiceMessageResponse("source_not_found")),
            StoreStatus.InvalidTargetFileName => TypedResults.BadRequest(
                new ServiceMessageResponse("invalid_target_file_name")),
            StoreStatus.ShareUnavailable => TypedResults.Json(
                new ServiceMessageResponse("share_unavailable"),
                statusCode: StatusCodes.Status503ServiceUnavailable),
            StoreStatus.CopyFailed => TypedResults.Json(
                new ServiceMessageResponse("copy_failed"),
                statusCode: StatusCodes.Status500InternalServerError),
            _ => TypedResults.Json(
                new ServiceMessageResponse("unknown_error"),
                statusCode: StatusCodes.Status500InternalServerError),
        };
    }
}
