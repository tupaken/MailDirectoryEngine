using ContactService.Domain.Contacts;

namespace ContactService.Domain.Abstractions;

internal interface IEwsContactClient : IDisposable
{
    Task<ContactPageDto> GetContactsPageAsync(int offset, int pageSize, CancellationToken ct);
    Task AddContactAsync(ContactDto dto, CancellationToken ct, string? sourceMessageId = null, long? observationId = null);
    Task<ContactWriteResult> UpsertContactAsync(ContactDto dto, CancellationToken ct, string? sourceMessageId = null, long? observationId = null);
}
