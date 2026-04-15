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
    }
}
