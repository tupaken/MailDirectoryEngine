using ContactService.Api.Endpoints;
using ContactService.Domain.Abstractions;
using ContactService.Infrastructure.Ews;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);

builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
});
builder.Services.AddSingleton<IEwsConfigProvider, EnvEwsConfigProvider>();
builder.Services.AddSingleton<IEwsContactClientFactory, EwsContactClientFactory>();

var app = builder.Build();

app.MapHealthEndpoints();
app.MapContactsEndpoints();

app.Run();
