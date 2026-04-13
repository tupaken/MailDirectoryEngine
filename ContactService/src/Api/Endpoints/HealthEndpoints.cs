namespace ContactService.Api.Endpoints;

internal static class HealthEndpoints
{
    /// <summary>
    /// Registers health-check endpoint for service liveness.
    /// </summary>
    /// <param name="app">Endpoint route builder instance.</param>
    /// <returns>The same route builder for chaining.</returns>
    public static IEndpointRouteBuilder MapHealthEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
        return app;
    }
}
