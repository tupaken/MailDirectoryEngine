using ContactService.Api.Contracts;
using ContactService.Application.Contacts;
using ContactService.Domain.Abstractions;

namespace ContactService.Api.Endpoints;

internal static class ContactsEndpoints
{
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
            IEwsContactClientFactory factory,
            IEwsConfigProvider configProvider,
            CancellationToken ct) =>
        {
            var validationError = CanonicalContactValidator.Validate(payload);
            if (validationError is not null)
                return Results.BadRequest(new { error = validationError });

            var resolvedAccountKey = ResolveAccountKey(payload.AccountKey);
            var dto = CanonicalContactMapper.ToContactDto(payload);
            var engine = new ExchangeContactEngine(factory, configProvider, resolvedAccountKey);

            await engine.AddContactAsync(dto, ct).ConfigureAwait(false);

            return Results.Ok(new ContactSyncResultDto(
                Status: "created",
                AccountKey: resolvedAccountKey,
                DisplayName: dto.DisplayName,
                Email: dto.Email,
                Phone: dto.BusinessPhone ?? dto.MobilePhone ?? dto.HomePhone));
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
