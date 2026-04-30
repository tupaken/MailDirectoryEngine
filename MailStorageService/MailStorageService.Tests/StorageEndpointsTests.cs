using MailStorageService.Api.Contracts;
using MailStorageService.Api.Endpoints;
using MailStorageService.Storage;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Http.HttpResults;

namespace MailStorageService.Tests;

public class StorageEndpointsTests
{
    /// <summary>
    /// Verifies that the health endpoint reports an ok status payload.
    /// </summary>
    [Fact]
    public void Health_ReturnsOkStatus()
    {
        var result = StorageEndpoints.Health();
        var payload = Assert.IsType<HealthResponse>(result.Value);

        Assert.Equal("ok", payload.Status);
    }

    /// <summary>
    /// Verifies that the store endpoint returns HTTP 200 when the engine stores the file successfully.
    /// </summary>
    [Fact]
    public void Store_ReturnsOk_WhenStorageSucceeds()
    {
        var result = StorageEndpoints.Store(
            new StoreRequest("/mail-export/message.eml", "12345", "test"),
            new FakeStorageEngine(StoreStatus.Success));

        var ok = Assert.IsType<Ok<ServiceMessageResponse>>(result.Result);
        var payload = Assert.IsType<ServiceMessageResponse>(ok.Value);

        Assert.Equal("200", payload.Message);
    }

    /// <summary>
    /// Verifies that the store endpoint returns HTTP 404 when the destination folder is missing.
    /// </summary>
    [Fact]
    public void Store_ReturnsNotFound_WhenDestinationFolderIsMissing()
    {
        var result = StorageEndpoints.Store(
            new StoreRequest("/mail-export/message.eml", "12345", "test"),
            new FakeStorageEngine(StoreStatus.DestinationNotFound));

        var notFound = Assert.IsType<NotFound<ServiceMessageResponse>>(result.Result);
        var payload = Assert.IsType<ServiceMessageResponse>(notFound.Value);

        Assert.Equal("destination_not_found", payload.Message);
    }

    /// <summary>
    /// Verifies that the store endpoint returns HTTP 404 when the source file is missing.
    /// </summary>
    [Fact]
    public void Store_ReturnsNotFound_WhenSourceFileIsMissing()
    {
        var result = StorageEndpoints.Store(
            new StoreRequest("/mail-export/message.eml", "12345", "test"),
            new FakeStorageEngine(StoreStatus.SourceNotFound));

        var notFound = Assert.IsType<NotFound<ServiceMessageResponse>>(result.Result);
        var payload = Assert.IsType<ServiceMessageResponse>(notFound.Value);

        Assert.Equal("source_not_found", payload.Message);
    }

    /// <summary>
    /// Verifies that the store endpoint returns HTTP 503 when the share is unavailable.
    /// </summary>
    [Fact]
    public void Store_ReturnsServiceUnavailable_WhenShareIsUnavailable()
    {
        var result = StorageEndpoints.Store(
            new StoreRequest("/mail-export/message.eml", "12345", "test"),
            new FakeStorageEngine(StoreStatus.ShareUnavailable));

        var json = Assert.IsType<JsonHttpResult<ServiceMessageResponse>>(result.Result);

        Assert.Equal(StatusCodes.Status503ServiceUnavailable, json.StatusCode);
        Assert.Equal("share_unavailable", json.Value?.Message);
    }

    /// <summary>
    /// Verifies that the store endpoint returns HTTP 400 when the target file name is invalid.
    /// </summary>
    [Fact]
    public void Store_ReturnsBadRequest_WhenTargetFileNameIsInvalid()
    {
        var result = StorageEndpoints.Store(
            new StoreRequest("/mail-export/message.eml", "12345", "../escape"),
            new FakeStorageEngine(StoreStatus.InvalidTargetFileName));

        var badRequest = Assert.IsType<BadRequest<ServiceMessageResponse>>(result.Result);
        var payload = Assert.IsType<ServiceMessageResponse>(badRequest.Value);

        Assert.Equal("invalid_target_file_name", payload.Message);
    }

    /// <summary>
    /// Verifies that the store endpoint returns HTTP 500 when copying fails unexpectedly.
    /// </summary>
    [Fact]
    public void Store_ReturnsInternalServerError_WhenCopyFails()
    {
        var result = StorageEndpoints.Store(
            new StoreRequest("/mail-export/message.eml", "12345", "test"),
            new FakeStorageEngine(StoreStatus.CopyFailed));

        var json = Assert.IsType<JsonHttpResult<ServiceMessageResponse>>(result.Result);

        Assert.Equal(StatusCodes.Status500InternalServerError, json.StatusCode);
        Assert.Equal("copy_failed", json.Value?.Message);
    }
}
