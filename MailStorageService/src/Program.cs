using DotNetEnv;
using MailStorageService.Storage;

var builder = WebApplication.CreateBuilder(args);

var envPath = Path.Combine(builder.Environment.ContentRootPath, ".env");
if (File.Exists(envPath))
{
    Env.Load(envPath);
}

var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.MapPost("/store", (StoreRequest request) =>
{
    var storageEngine = new StorageEngine();
    var success = storageEngine.Store(request.SourcePath, request.Number);

    return success
        ? Results.Ok(new { message = "200" })
        : Results.BadRequest(new { message = "400" });
});

app.Run();

internal sealed record StoreRequest(string SourcePath, string Number);
