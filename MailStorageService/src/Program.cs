using DotNetEnv;
using MailStorageService.Storage;
using Sprache;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

Env.Load(Path.Combine(builder.Environment.ContentRootPath, ".env"));

app.MapPost("/store", (StoreRequest request) =>
{
    var storageEngine = new StorageEngine();
    var success = storageEngine.Store( request.SourcePath,request.Number);

    return success
        ? Results.Ok(new {message = "200"})
        : Results.BadRequest(new {message = "400"});
} );


app.Run();

internal sealed record StoreRequest(string SourcePath, string Number);