using MailStorageService.Api.Contracts;
using MailStorageService.Api.Endpoints;
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
            new StoreRequest("/mail-export/message.eml", "12345"),
            new FakeStorageEngine(true));

        var ok = Assert.IsType<Ok<ServiceMessageResponse>>(result.Result);
        var payload = Assert.IsType<ServiceMessageResponse>(ok.Value);

        Assert.Equal("200", payload.Message);
    }

    /// <summary>
    /// Verifies that the store endpoint returns HTTP 400 when the engine cannot store the file.
    /// </summary>
    [Fact]
    public void Store_ReturnsBadRequest_WhenStorageFails()
    {
        var result = StorageEndpoints.Store(
            new StoreRequest("/mail-export/message.eml", "12345"),
            new FakeStorageEngine(false));

        var badRequest = Assert.IsType<BadRequest<ServiceMessageResponse>>(result.Result);
        var payload = Assert.IsType<ServiceMessageResponse>(badRequest.Value);

        Assert.Equal("400", payload.Message);
    }
}
