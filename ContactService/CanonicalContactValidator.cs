internal static class CanonicalContactValidator
{
    public static string? Validate(CanonicalContactEnvelopeDto? payload)
    {
        if (payload is null)
            return "Payload is required.";

        if (!string.Equals(payload.SchemaVersion, CanonicalContactSchema.Version, StringComparison.Ordinal))
        {
            return $"Unsupported schema_version '{payload.SchemaVersion}'. " +
                   $"Expected '{CanonicalContactSchema.Version}'.";
        }

        if (payload.Contact is null)
            return "contact is required.";

        var hasName =
            !string.IsNullOrWhiteSpace(payload.Contact.FullName) ||
            !string.IsNullOrWhiteSpace(payload.Contact.GivenName) ||
            !string.IsNullOrWhiteSpace(payload.Contact.Surname);
        if (!hasName)
            return "contact.full_name or (contact.given_name + contact.surname) is required.";

        var phones = payload.Contact.Phones ?? Array.Empty<CanonicalPhoneDto>();
        var hasPhone = phones.Any(phone =>
            !string.IsNullOrWhiteSpace(phone.Raw) ||
            !string.IsNullOrWhiteSpace(phone.E164));
        if (!hasPhone)
            return "contact.phones must contain at least one number.";

        return null;
    }
}
