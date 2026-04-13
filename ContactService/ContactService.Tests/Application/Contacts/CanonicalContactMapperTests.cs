using ContactService.Api.Contracts;
using ContactService.Application.Contacts;
using Xunit;

namespace ContactService.Tests.Application.Contacts;

public class CanonicalContactMapperTests
{
    /// <summary>
    /// Verifies that full name is normalized and split into given name and surname.
    /// </summary>
    [Fact]
    public void ToContactDto_SplitsFullName_AndMapsPrimaryEmail()
    {
        var payload = BuildPayload(
            fullName: "  Ada Lovelace  ",
            givenName: null,
            surname: null,
            email: "ada@example.test",
            phones: new List<CanonicalPhoneDto>
            {
                new(Type: "business", Raw: "+49 30 123456", E164: null)
            });

        var dto = CanonicalContactMapper.ToContactDto(payload);

        Assert.Equal("Ada Lovelace", dto.DisplayName);
        Assert.Equal("Ada", dto.GivenName);
        Assert.Equal("Lovelace", dto.Surname);
        Assert.Equal("ada@example.test", dto.Email);
        Assert.Equal("ada@example.test", dto.Emails["EmailAddress1"]);
        Assert.Equal("Ada Lovelace", dto.EmailDisplayNames["EmailAddress1"]);
        Assert.Equal("Ada Lovelace", dto.FileAs);
    }

    /// <summary>
    /// Verifies that missing name, email, and phone data falls back to a stable placeholder display name.
    /// </summary>
    [Fact]
    public void ToContactDto_UsesUnknownContact_WhenNameEmailAndPhonesAreMissing()
    {
        var payload = BuildPayload(
            fullName: " ",
            givenName: " ",
            surname: " ",
            email: " ",
            phones: new List<CanonicalPhoneDto>(),
            sourceMessageId: null,
            address: null,
            notes: null);

        var dto = CanonicalContactMapper.ToContactDto(payload);

        Assert.Equal("Unknown Contact", dto.DisplayName);
        Assert.Null(dto.Email);
        Assert.Null(dto.BusinessPhone);
        Assert.Null(dto.HomePhone);
        Assert.Null(dto.MobilePhone);
        Assert.Null(dto.BusinessFax);
        Assert.Null(dto.Notes);
        Assert.Empty(dto.Emails);
        Assert.Empty(dto.EmailDisplayNames);
    }

    /// <summary>
    /// Verifies primary and additional phone slot selection including duplicate suppression.
    /// </summary>
    [Fact]
    public void ToContactDto_MapsPrimaryPhones_AndAdditionalPhoneSlots()
    {
        var payload = BuildPayload(
            fullName: "Max Mustermann",
            givenName: null,
            surname: null,
            email: "max@example.test",
            phones: new List<CanonicalPhoneDto>
            {
                new(Type: "business", Raw: "030-1234", E164: null),
                new(Type: "business", Raw: "0301234", E164: null),
                new(Type: "mobile", Raw: null, E164: "+49171111"),
                new(Type: "home", Raw: "040 999", E164: null),
                new(Type: "fax", Raw: "030 777", E164: null),
                new(Type: "business", Raw: "030 888", E164: null),
                new(Type: "home", Raw: "040 111", E164: null),
                new(Type: "other", Raw: "0800 1", E164: null)
            });

        var dto = CanonicalContactMapper.ToContactDto(payload);

        Assert.Equal("030-1234", dto.BusinessPhone);
        Assert.Equal("+49171111", dto.MobilePhone);
        Assert.Equal("040 999", dto.HomePhone);
        Assert.Equal("030 777", dto.BusinessFax);

        Assert.Equal("030 888", dto.PhoneNumbers["BusinessPhone2"]);
        Assert.Equal("040 111", dto.PhoneNumbers["HomePhone2"]);
        Assert.Equal("0800 1", dto.PhoneNumbers["CompanyMainPhone"]);
        Assert.Equal(3, dto.PhoneNumbers.Count);
    }

    /// <summary>
    /// Verifies that notes are composed from source id, address, and free-form notes.
    /// </summary>
    [Fact]
    public void ToContactDto_ComposesNotes_FromSourceAddressAndNotes()
    {
        var payload = BuildPayload(
            fullName: "Max Mustermann",
            givenName: null,
            surname: null,
            email: "max@example.test",
            phones: new List<CanonicalPhoneDto>
            {
                new(Type: "business", Raw: "030 1234", E164: null)
            },
            sourceMessageId: "  mail-99  ",
            address: "  Hauptstrasse 10  ",
            notes: "  Rueckruf am Nachmittag  ");

        var dto = CanonicalContactMapper.ToContactDto(payload);

        Assert.Equal(
            string.Join(
                Environment.NewLine,
                "source_message_id=mail-99",
                "address=Hauptstrasse 10",
                "Rueckruf am Nachmittag"),
            dto.Notes);
    }

    private static CanonicalContactEnvelopeDto BuildPayload(
        string? fullName,
        string? givenName,
        string? surname,
        string? email,
        IReadOnlyList<CanonicalPhoneDto>? phones,
        string? sourceMessageId = "mail-42",
        string? address = "Musterstrasse 1",
        string? notes = "Bitte Rueckruf")
    {
        return new CanonicalContactEnvelopeDto(
            SchemaVersion: CanonicalContactSchema.Version,
            Contact: new CanonicalContactDto(
                FullName: fullName,
                GivenName: givenName,
                Surname: surname,
                Company: "Muster GmbH",
                Email: email,
                Phones: phones,
                Address: address,
                Website: "example.test",
                Notes: notes),
            AccountKey: "bewerbung",
            SourceMessageId: sourceMessageId);
    }
}
