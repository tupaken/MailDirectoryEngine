using ContactService.Api.Contracts;
using ContactService.Application.Contacts;
using Xunit;

namespace ContactService.Tests.Application.Contacts;

public class CanonicalContactValidatorTests
{
    /// <summary>
    /// Verifies that validation rejects a missing payload.
    /// </summary>
    [Fact]
    public void Validate_ReturnsError_WhenPayloadIsNull()
    {
        var error = CanonicalContactValidator.Validate(null);

        Assert.Equal("Payload is required.", error);
    }

    /// <summary>
    /// Verifies that unsupported schema versions are rejected.
    /// </summary>
    [Fact]
    public void Validate_ReturnsError_WhenSchemaVersionIsUnsupported()
    {
        var payload = new CanonicalContactEnvelopeDto(
            SchemaVersion: "2.0",
            Contact: BuildContact(),
            AccountKey: "testaccount",
            SourceMessageId: "mail-1");

        var error = CanonicalContactValidator.Validate(payload);

        Assert.Equal(
            "Unsupported schema_version '2.0'. Expected '1.0'.",
            error);
    }

    /// <summary>
    /// Verifies that validation rejects a missing contact object.
    /// </summary>
    [Fact]
    public void Validate_ReturnsError_WhenContactIsNull()
    {
        var payload = new CanonicalContactEnvelopeDto(
            SchemaVersion: CanonicalContactSchema.Version,
            Contact: null!,
            AccountKey: "testaccount",
            SourceMessageId: "mail-1");

        var error = CanonicalContactValidator.Validate(payload);

        Assert.Equal("contact is required.", error);
    }

    /// <summary>
    /// Verifies that at least one name field is required.
    /// </summary>
    [Fact]
    public void Validate_ReturnsError_WhenNameIsMissing()
    {
        var payload = new CanonicalContactEnvelopeDto(
            SchemaVersion: CanonicalContactSchema.Version,
            Contact: new CanonicalContactDto(
                FullName: " ",
                GivenName: null,
                Surname: null,
                Company: null,
                Email: "max@example.test",
                Phones: new List<CanonicalPhoneDto>
                {
                    new(Type: "business", Raw: "+49 30 123456", E164: null)
                },
                Address: null,
                Website: null,
                Notes: null),
            AccountKey: "testaccount",
            SourceMessageId: null);

        var error = CanonicalContactValidator.Validate(payload);

        Assert.Equal(
            "contact.full_name or (contact.given_name + contact.surname) is required.",
            error);
    }

    /// <summary>
    /// Verifies that at least one phone number is required.
    /// </summary>
    [Fact]
    public void Validate_ReturnsError_WhenPhonesAreMissing()
    {
        var payload = new CanonicalContactEnvelopeDto(
            SchemaVersion: CanonicalContactSchema.Version,
            Contact: new CanonicalContactDto(
                FullName: "Max Mustermann",
                GivenName: null,
                Surname: null,
                Company: null,
                Email: "max@example.test",
                Phones: new List<CanonicalPhoneDto>
                {
                    new(Type: "business", Raw: " ", E164: null)
                },
                Address: null,
                Website: null,
                Notes: null),
            AccountKey: "testaccount",
            SourceMessageId: null);

        var error = CanonicalContactValidator.Validate(payload);

        Assert.Equal("contact.phones must contain at least one number.", error);
    }

    /// <summary>
    /// Verifies that a valid payload passes validation.
    /// </summary>
    [Fact]
    public void Validate_ReturnsNull_WhenPayloadIsValid()
    {
        var payload = new CanonicalContactEnvelopeDto(
            SchemaVersion: CanonicalContactSchema.Version,
            Contact: BuildContact(),
            AccountKey: "testaccount",
            SourceMessageId: "mail-1");

        var error = CanonicalContactValidator.Validate(payload);

        Assert.Null(error);
    }

    private static CanonicalContactDto BuildContact()
    {
        return new CanonicalContactDto(
            FullName: "Max Mustermann",
            GivenName: null,
            Surname: null,
            Company: "Muster GmbH",
            Email: "max@example.test",
            Phones: new List<CanonicalPhoneDto>
            {
                new(Type: "business", Raw: "+49 30 123456", E164: null)
            },
            Address: "Musterstrasse 1",
            Website: "example.test",
            Notes: "Bitte Rueckruf");
    }
}
