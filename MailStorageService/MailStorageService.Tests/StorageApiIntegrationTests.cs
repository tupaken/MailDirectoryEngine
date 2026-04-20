using System.Net;
using System.Net.Http.Json;
using MailStorageService.Api.Contracts;
using MailStorageService.Storage;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace MailStorageService.Tests;

public class StorageApiIntegrationTests
{
    /// <summary>
    /// Verifies that a correctly shaped JSON request body is bound and processed successfully.
    /// </summary>
    [Fact]
    public async Task PostStore_ReturnsOk_WhenJsonBodyUsesSourcePath()
    {
        await using var factory = new StorageApiFactory(new FakeStorageEngine(true));
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync(
            "/store",
            new
            {
                sourcePath = "/mail-export/250_0ed2d9.eml",
                number = "26010"
            });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var payload = await response.Content.ReadFromJsonAsync<ServiceMessageResponse>();

        Assert.NotNull(payload);
        Assert.Equal("200", payload.Message);
    }

    private sealed class StorageApiFactory : WebApplicationFactory<Program>
    {
        private readonly IStorageEngine storageEngine;

        public StorageApiFactory(IStorageEngine storageEngine)
        {
            this.storageEngine = storageEngine;
        }

        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            builder.UseEnvironment("Development");
            builder.ConfigureTestServices(services =>
            {
                services.AddSingleton(this.storageEngine);
                services.AddSingleton<IStorageEngine>(this.storageEngine);
            });
        }
    }
}
