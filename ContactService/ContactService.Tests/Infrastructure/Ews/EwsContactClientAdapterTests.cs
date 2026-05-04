using ContactService.Domain.Abstractions;
using ContactService.Domain.Contacts;
using ContactService.Infrastructure.Ews;
using Microsoft.Exchange.WebServices.Data;
using Xunit;

namespace ContactService.Tests.Infrastructure.Ews;

public class EwsContactClientAdapterTests
{
    [Fact]
    public async System.Threading.Tasks.Task AddContactAsync_DeletesSavedContact_WhenStoreInsertFails()
    {
        var store = new FakeContactStore
        {
            InsertException = new InvalidOperationException("db failed")
        };
        var deletedIds = new List<string>();
        var adapter = new EwsContactClientAdapter(
            new ExchangeService(ExchangeVersion.Exchange2013_SP1),
            store,
            saveContactAsync: (_, _) => System.Threading.Tasks.Task.FromResult("ews-123"),
            deleteContactAsync: ewsItemId =>
            {
                deletedIds.Add(ewsItemId);
                return System.Threading.Tasks.Task.CompletedTask;
            });

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(
            () => adapter.AddContactAsync(BuildContact("Rollback"), CancellationToken.None, "42"));

        Assert.Equal("db failed", ex.Message);
        Assert.Equal(new[] { "ews-123" }, deletedIds);
        Assert.Equal(1, store.InsertCalls);
        Assert.Equal("42", store.ReceivedSourceMessageId);
    }

    [Fact]
    public async System.Threading.Tasks.Task AddContactAsync_SurfacesRollbackFailure_WhenDeleteAlsoFails()
    {
        var store = new FakeContactStore
        {
            InsertException = new InvalidOperationException("db failed")
        };
        var adapter = new EwsContactClientAdapter(
            new ExchangeService(ExchangeVersion.Exchange2013_SP1),
            store,
            saveContactAsync: (_, _) => System.Threading.Tasks.Task.FromResult("ews-123"),
            deleteContactAsync: _ => throw new InvalidOperationException("delete failed"));

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(
            () => adapter.AddContactAsync(BuildContact("Rollback"), CancellationToken.None));

        Assert.Contains("rollback delete failed", ex.Message);
        var aggregate = Assert.IsType<AggregateException>(ex.InnerException);
        Assert.Collection(
            aggregate.InnerExceptions,
            item => Assert.Equal("db failed", item.Message),
            item => Assert.Equal("delete failed", item.Message));
    }

    [Fact]
    public async System.Threading.Tasks.Task AddContactAsync_LogsCreatedChange_WhenInsertSucceeds()
    {
        var store = new FakeContactStore();
        var adapter = new EwsContactClientAdapter(
            new ExchangeService(ExchangeVersion.Exchange2013_SP1),
            store,
            saveContactAsync: (_, _) => System.Threading.Tasks.Task.FromResult("ews-123"),
            deleteContactAsync: _ => System.Threading.Tasks.Task.CompletedTask);

        await adapter.AddContactAsync(BuildContact("Created Contact"), CancellationToken.None, "mail-42", 99);

        var change = Assert.Single(store.ChangeLogs);
        Assert.Equal(1, change.ContactId);
        Assert.Equal("ews-123", change.EwsId);
        Assert.Equal(99, change.ObservationId);
        Assert.Equal("created", change.Action);
        Assert.Null(change.FieldName);
        Assert.Equal("Created Contact", change.NewValue);
        Assert.Equal("mail-42", change.SourceMessageId);
        Assert.Equal("promoted_observation_created_contact", change.Reason);
    }

    private static ContactDto BuildContact(string displayName)
    {
        return new ContactDto(
            Id: null,
            DisplayName: displayName,
            GivenName: null,
            MiddleName: null,
            Surname: null,
            Company: null,
            JobTitle: null,
            FileAs: displayName,
            WebPage: null,
            EmailDisplayNames: new Dictionary<string, string>(),
            Emails: new Dictionary<string, string>(),
            ImAddresses: new Dictionary<string, string>(),
            PhoneNumbers: new Dictionary<string, string>(),
            Addresses: new Dictionary<string, ContactAddressDto>(),
            PostalAddressKey: null,
            Email: null,
            BusinessPhone: null,
            HomePhone: null,
            BusinessFax: null,
            MobilePhone: null,
            Notes: null);
    }

    private sealed class FakeContactStore : IContactStore
    {
        public Exception? InsertException { get; init; }

        public int InsertCalls { get; private set; }

        public string? ReceivedSourceMessageId { get; private set; }

        public List<ChangeLogCall> ChangeLogs { get; } = new();

        public System.Threading.Tasks.Task<string?> ExistsAsync(ContactDto dto, CancellationToken ct)
        {
            return System.Threading.Tasks.Task.FromResult<string?>(null);
        }

        public System.Threading.Tasks.Task<long> InsertAsync(
            ContactDto dto,
            string ewsId,
            string? sourceMessageId,
            CancellationToken ct)
        {
            InsertCalls++;
            ReceivedSourceMessageId = sourceMessageId;

            if (InsertException is not null)
                throw InsertException;

            return System.Threading.Tasks.Task.FromResult(1L);
        }

        public System.Threading.Tasks.Task<long?> FindContactIdByEwsIdAsync(string ewsId, CancellationToken ct)
        {
            return System.Threading.Tasks.Task.FromResult<long?>(1);
        }

        public System.Threading.Tasks.Task UpdateFromPromotedObservationAsync(
            ContactDto dto,
            string ewsId,
            string? sourceMessageId,
            CancellationToken ct)
        {
            return System.Threading.Tasks.Task.CompletedTask;
        }

        public System.Threading.Tasks.Task<ContactObservationRecord> UpsertObservationAsync(
            ContactObservationRecord observation,
            CancellationToken ct)
        {
            return System.Threading.Tasks.Task.FromResult(observation with { Id = 1 });
        }

        public System.Threading.Tasks.Task MarkObservationStatusAsync(
            long observationId,
            string status,
            string? reason,
            string? promotedContactEwsId,
            CancellationToken ct)
        {
            return System.Threading.Tasks.Task.CompletedTask;
        }

        public System.Threading.Tasks.Task<int> CountDistinctNamesForPhoneAsync(
            string phoneDigits,
            string? fullName,
            CancellationToken ct)
        {
            return System.Threading.Tasks.Task.FromResult(0);
        }

        public System.Threading.Tasks.Task<int> CountDistinctNamesForEmailAsync(
            string normalizedEmail,
            string? fullName,
            CancellationToken ct)
        {
            return System.Threading.Tasks.Task.FromResult(0);
        }

        public System.Threading.Tasks.Task<ExistingContactIdentity?> FindExistingContactByEmailAsync(
            string normalizedEmail,
            CancellationToken ct)
        {
            return System.Threading.Tasks.Task.FromResult<ExistingContactIdentity?>(null);
        }

        public System.Threading.Tasks.Task<int> CountExistingContactsForPhoneAsync(
            string phoneDigits,
            string? normalizedEmail,
            CancellationToken ct)
        {
            return System.Threading.Tasks.Task.FromResult(0);
        }

        public System.Threading.Tasks.Task InsertChangeLogAsync(
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
            return System.Threading.Tasks.Task.CompletedTask;
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
}
