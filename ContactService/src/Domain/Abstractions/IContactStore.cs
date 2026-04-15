

using ContactService.Domain.Contacts;

namespace ContactService.Domain.Abstractions;

internal interface IContactStore
{
    Task<string?> ExistsAsync(ContactDto dto, CancellationToken ct);
    Task<long> InsertAsync(ContactDto dto,string ewsId, string? sourceMessageId, CancellationToken ct);
}
