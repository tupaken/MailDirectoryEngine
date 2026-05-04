using ContactService.Api.Contracts;
using ContactService.Application.Contacts;
using ContactService.Domain.Abstractions;

namespace ContactService.Api.Endpoints;

internal static class ContactsEndpoints
{
    /// <summary>
    /// Registers contact read and canonical ingest endpoints.
    /// </summary>
    /// <param name="app">Endpoint route builder instance.</param>
    /// <returns>The same route builder for chaining.</returns>
    public static IEndpointRouteBuilder MapContactsEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/contacts", async Task<IResult> (
            int? pageSize,
            string? accountKey,
            IEwsContactClientFactory factory,
            IEwsConfigProvider configProvider,
            CancellationToken ct) =>
        {
            var resolvedPageSize = pageSize is > 0 and <= 500 ? pageSize.Value : 100;
            var resolvedAccountKey = ResolveAccountKey(accountKey);

            var engine = new ExchangeContactEngine(factory, configProvider, resolvedAccountKey);
            var contacts = await engine.GetAllContactsAsync(resolvedPageSize, ct).ConfigureAwait(false);

            return Results.Ok(new
            {
                account_key = resolvedAccountKey,
                count = contacts.Count,
                items = contacts
            });
        });

        app.MapPost("/api/contacts/canonical", async Task<IResult> (
            CanonicalContactEnvelopeDto payload,
            IContactStore contactStore,
            IEwsContactClientFactory factory,
            IEwsConfigProvider configProvider,
            CancellationToken ct) =>
        {
            var validationError = CanonicalContactValidator.Validate(payload);
            if (validationError is not null)
                return Results.BadRequest(new { error = validationError });

            var resolvedAccountKey = ResolveAccountKey(payload.AccountKey);
            var engine = new ContactObservationEngine(contactStore, factory, configProvider, resolvedAccountKey);
            var result = await engine.IngestAsync(payload, ct).ConfigureAwait(false);

            return Results.Ok(result);
        });

        app.MapPost("/api/contacts/observations", async Task<IResult> (
            CanonicalContactEnvelopeDto payload,
            IContactStore contactStore,
            IEwsContactClientFactory factory,
            IEwsConfigProvider configProvider,
            CancellationToken ct) =>
        {
            var validationError = CanonicalContactValidator.Validate(payload);
            if (validationError is not null)
                return Results.BadRequest(new { error = validationError });

            var resolvedAccountKey = ResolveAccountKey(payload.AccountKey);
            var engine = new ContactObservationEngine(contactStore, factory, configProvider, resolvedAccountKey);
            var result = await engine.IngestAsync(payload, ct).ConfigureAwait(false);

            return Results.Ok(result);
        });

        return app;
    }

    private static string ResolveAccountKey(string? accountKey)
    {
        if (!string.IsNullOrWhiteSpace(accountKey))
            return accountKey.Trim();

        var fallback = Environment.GetEnvironmentVariable("EWS_ACCOUNT_KEY");
        return string.IsNullOrWhiteSpace(fallback) ? "bewerbung" : fallback.Trim();
    }
}
