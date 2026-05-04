using ContactService.Api.Contracts;
using ContactService.Application.Contacts;
using ContactService.Domain.Abstractions;
using ContactService.Domain.Contacts;
using Xunit;

namespace ContactService.Tests.Application.Contacts;

public class ContactObservationEngineTests
{
    [Fact]
    public async Task IngestAsync_KeepsObservationPending_WhenEmailIsMissing()
    {
        var store = new FakeContactStore();
        var factory = new FakeEwsContactClientFactory();
        var engine = new ContactObservationEngine(store, factory, new FakeEwsConfigProvider(), "testaccount");

        var result = await engine.IngestAsync(
            BuildPayload(email: "", evidence: StrongEvidence()),
            CancellationToken.None);

        Assert.Equal("pending", result.Status);
        Assert.Equal("email_required_for_exchange_promotion", result.Reason);
        Assert.Equal(0, factory.Client.UpsertCalls);
        Assert.Equal("pending", store.MarkedStatus);
        var change = Assert.Single(store.ChangeLogs);
        Assert.Equal("pending", change.Action);
        Assert.Equal(17, change.ObservationId);
        Assert.Equal("email_required_for_exchange_promotion", change.Reason);
    }

    [Fact]
    public async Task IngestAsync_MarksSuspicious_WhenPhoneWasSeenWithDifferentName()
    {
        var store = new FakeContactStore { PhoneNameConflictCount = 1 };
        var factory = new FakeEwsContactClientFactory();
        var engine = new ContactObservationEngine(store, factory, new FakeEwsConfigProvider(), "testaccount");

        var result = await engine.IngestAsync(
            BuildPayload(email: "ada@example.test", evidence: StrongEvidence()),
            CancellationToken.None);

        Assert.Equal("suspicious", result.Status);
        Assert.Equal("phone_seen_with_different_name", result.Reason);
        Assert.Equal(0, factory.Client.UpsertCalls);
        var change = Assert.Single(store.ChangeLogs);
        Assert.Equal("suspicious", change.Action);
        Assert.Equal("phone_seen_with_different_name", change.Reason);
    }

    [Fact]
    public async Task IngestAsync_PromotesStrongLocalContext()
    {
        var store = new FakeContactStore();
        var factory = new FakeEwsContactClientFactory();
        var engine = new ContactObservationEngine(store, factory, new FakeEwsConfigProvider(), "testaccount");

        var result = await engine.IngestAsync(
            BuildPayload(email: "ada@example.test", evidence: StrongEvidence()),
            CancellationToken.None);

        Assert.Equal("promoted", result.Status);
        Assert.Equal("strong_local_context", result.Reason);
        Assert.Equal("created", result.ExchangeStatus);
        Assert.Equal(1, factory.Client.UpsertCalls);
        Assert.Equal("promoted", store.MarkedStatus);
        Assert.Equal("ews-42", store.MarkedPromotedEwsId);
    }

    [Fact]
    public async Task IngestAsync_MarksSuspicious_WhenExistingEmailHasDifferentName()
    {
        var store = new FakeContactStore
        {
            ExistingEmailContact = new ExistingContactIdentity(
                Id: 100,
                EwsId: "ews-existing",
                DisplayName: "Grace Hopper",
                FullName: "Grace Hopper",
                Company: "Analytical Engines",
                NormalizedEmail: "ada@example.test")
        };
        var factory = new FakeEwsContactClientFactory();
        var engine = new ContactObservationEngine(store, factory, new FakeEwsConfigProvider(), "testaccount");

        var result = await engine.IngestAsync(
            BuildPayload(email: "ada@example.test", evidence: StrongEvidence()),
            CancellationToken.None);

        Assert.Equal("suspicious", result.Status);
        Assert.Equal("existing_email_has_different_identity", result.Reason);
        Assert.Equal(0, factory.Client.UpsertCalls);
    }

    [Fact]
    public async Task IngestAsync_MarksSuspicious_WhenPhoneBelongsToExistingDifferentEmail()
    {
        var store = new FakeContactStore { ExistingPhoneContactCount = 1 };
        var factory = new FakeEwsContactClientFactory();
        var engine = new ContactObservationEngine(store, factory, new FakeEwsConfigProvider(), "testaccount");

        var result = await engine.IngestAsync(
            BuildPayload(email: "ada@example.test", evidence: StrongEvidence()),
            CancellationToken.None);

        Assert.Equal("suspicious", result.Status);
        Assert.Equal("phone_already_belongs_to_existing_contact", result.Reason);
        Assert.Equal(0, factory.Client.UpsertCalls);
    }

    private static CanonicalContactEnvelopeDto BuildPayload(
        string email,
        CanonicalContactEvidenceDto evidence)
    {
        return new CanonicalContactEnvelopeDto(
            SchemaVersion: CanonicalContactSchema.Version,
            Contact: new CanonicalContactDto(
                FullName: "Ada Lovelace",
                GivenName: null,
                Surname: null,
                Company: "Analytical Engines",
                Email: email,
                Phones: new List<CanonicalPhoneDto>
                {
                    new(Type: "business", Raw: "+49 30 123456", E164: "+4930123456")
                },
                Address: null,
                Website: null,
                Notes: null),
            AccountKey: "testaccount",
            SourceMessageId: "mail-1",
            Evidence: evidence);
    }

    private static CanonicalContactEvidenceDto StrongEvidence()
    {
        return new CanonicalContactEvidenceDto(
            SourceKind: "local_contact_block",
            EmailInSourceBlock: true,
            PhoneInSourceBlock: true,
            NameInSourceBlock: true,
            CompanyInSourceBlock: false);
    }

    private sealed class FakeContactStore : IContactStore
    {
        public int PhoneNameConflictCount { get; init; }

        public int ExistingPhoneContactCount { get; init; }

        public ExistingContactIdentity? ExistingEmailContact { get; init; }

        public string? MarkedStatus { get; private set; }

        public string? MarkedPromotedEwsId { get; private set; }

        public List<ChangeLogCall> ChangeLogs { get; } = new();

        public Task<string?> ExistsAsync(ContactDto dto, CancellationToken ct)
        {
            return Task.FromResult<string?>(null);
        }

        public Task<long> InsertAsync(ContactDto dto, string ewsId, string? sourceMessageId, CancellationToken ct)
        {
            return Task.FromResult(1L);
        }

        public Task<long?> FindContactIdByEwsIdAsync(string ewsId, CancellationToken ct)
        {
            return Task.FromResult<long?>(1);
        }

        public Task UpdateFromPromotedObservationAsync(
            ContactDto dto,
            string ewsId,
            string? sourceMessageId,
            CancellationToken ct)
        {
            return Task.CompletedTask;
        }

        public Task<ContactObservationRecord> UpsertObservationAsync(
            ContactObservationRecord observation,
            CancellationToken ct)
        {
            return Task.FromResult(observation with { Id = 17 });
        }

        public Task MarkObservationStatusAsync(
            long observationId,
            string status,
            string? reason,
            string? promotedContactEwsId,
            CancellationToken ct)
        {
            MarkedStatus = status;
            MarkedPromotedEwsId = promotedContactEwsId;
            return Task.CompletedTask;
        }

        public Task<int> CountDistinctNamesForPhoneAsync(string phoneDigits, string? fullName, CancellationToken ct)
        {
            return Task.FromResult(PhoneNameConflictCount);
        }

        public Task<int> CountDistinctNamesForEmailAsync(string normalizedEmail, string? fullName, CancellationToken ct)
        {
            return Task.FromResult(0);
        }

        public Task<ExistingContactIdentity?> FindExistingContactByEmailAsync(
            string normalizedEmail,
            CancellationToken ct)
        {
            return Task.FromResult(ExistingEmailContact);
        }

        public Task<int> CountExistingContactsForPhoneAsync(
            string phoneDigits,
            string? normalizedEmail,
            CancellationToken ct)
        {
            return Task.FromResult(ExistingPhoneContactCount);
        }

        public Task InsertChangeLogAsync(
            long? contactId,
            string? ewsId,
            long? observationId,
            string action,
            string? fieldName,
            string? oldValue,
            string? newValue,
            string? sourceMessageId,
            string? reason,
            CancellationToken ct)
        {
            ChangeLogs.Add(new ChangeLogCall(
                contactId,
                ewsId,
                observationId,
                action,
                fieldName,
                oldValue,
                newValue,
                sourceMessageId,
                reason));
            return Task.CompletedTask;
        }
    }

    private sealed record ChangeLogCall(
        long? ContactId,
        string? EwsId,
        long? ObservationId,
        string Action,
        string? FieldName,
        string? OldValue,
        string? NewValue,
        string? SourceMessageId,
        string? Reason);

    private sealed class FakeEwsConfigProvider : IEwsConfigProvider
    {
        public EwsConfig GetConfig(string accountKey)
        {
            return new EwsConfig
            {
                ServiceUrl = "https://ews.example.test/EWS/Exchange.asmx",
                Mailbox = "contact@example.test",
                OAuthAccessToken = "token"
            };
        }
    }

    private sealed class FakeEwsContactClientFactory : IEwsContactClientFactory
    {
        public FakeEwsContactClient Client { get; } = new();

        public IEwsContactClient Create(EwsConfig config)
        {
            return Client;
        }
    }

    private sealed class FakeEwsContactClient : IEwsContactClient
    {
        public int UpsertCalls { get; private set; }

        public Task<ContactPageDto> GetContactsPageAsync(int offset, int pageSize, CancellationToken ct)
        {
            return Task.FromResult(new ContactPageDto(Array.Empty<ContactDto>(), null));
        }

        public Task AddContactAsync(ContactDto dto, CancellationToken ct, string? sourceMessageId = null, long? observationId = null)
        {
            return Task.CompletedTask;
        }

        public Task<ContactWriteResult> UpsertContactAsync(
            ContactDto dto,
            CancellationToken ct,
            string? sourceMessageId = null,
            long? observationId = null)
        {
            UpsertCalls++;
            return Task.FromResult(new ContactWriteResult("created", "ews-42"));
        }

        public void Dispose()
        {
        }
    }
}
