using ContactService.Domain.Abstractions;
using ContactService.Infrastructure.DB;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;

namespace ContactService.Api.DependencyInjection;

internal static class DatabaseRegistration
{
    /// <summary>
    /// Registers PostgreSQL infrastructure used by ContactService.
    /// </summary>
    /// <param name="services">Service collection to extend.</param>
    /// <returns>The same service collection for chaining.</returns>
    public static IServiceCollection AddPostgres(this IServiceCollection services)
    {
        services.AddSingleton<NpgsqlDataSource>(_ =>
        {
            var csb = new NpgsqlConnectionStringBuilder
            {
                Host=Environment.GetEnvironmentVariable("POSTGRES_HOST") ?? "localhost",
                Port=int.TryParse(Environment.GetEnvironmentVariable("POSTGRES_PORT"),out var port) ? port : 5432,
                Database = RequireEnv("POSTGRES_DB"),
                Username = RequireEnv("POSTGRES_USER"),
                Password = RequireEnv("POSTGRES_PASSWORD"),
                Pooling = true
            }; 
            return  NpgsqlDataSource.Create(csb.ConnectionString);
        });
        services.AddSingleton<IContactStore, PostgresContactStore>();
        return services;
    }

    /// <summary>
    /// Reads one required environment variable and throws when it is missing.
    /// </summary>
    /// <param name="key">Environment variable name to resolve.</param>
    /// <returns>The non-empty environment variable value.</returns>
    private static string RequireEnv(string key)
    {
        var value = Environment.GetEnvironmentVariable(key);
        if (string.IsNullOrEmpty(value))
            throw new InvalidOperationException($"Missing env var: {key}");
        return value;
    }
    
}
