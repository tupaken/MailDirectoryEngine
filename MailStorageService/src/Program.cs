using DotNetEnv;
using MailStorageService.Api.Endpoints;
using MailStorageService.Storage;

var builder = WebApplication.CreateBuilder(args);

var envPath = Path.Combine(builder.Environment.ContentRootPath, ".env");
if (File.Exists(envPath))
{
    Env.Load(envPath);
}

builder.Services.AddSingleton<IStorageEngine, StorageEngine>();

var app = builder.Build();

app.MapStorageEndpoints();

app.Run();

/// <summary>
/// Entry point for the mail storage HTTP service.
/// </summary>
public partial class Program;
