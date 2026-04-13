using ContactService.Domain.Abstractions;
using ContactService.Domain.Contacts;
using Npgsql;

namespace ContactService.Infrastructure.DB;

internal sealed class PostgresContactStore : IContactStore
{
    private readonly NpgsqlDataSource _dataSource;

    public PostgresContactStore(NpgsqlDataSource dataSource)=> _dataSource = dataSource;
    public async Task<bool> ExistsAsync(ContactDto dto, CancellationToken ct)
    {
        const string sql = """" 
            SELECT EXISTS (
                SELECT 1
                FROM contacts c
                WHERE
                    (@email IS NOT NULL AND c.email IS NOT NULL AND c.email = @email)
                    OR (@business_phone IS NOT NULL AND c.business_phone IS NOT NULL AND c.business_phone = @business_phone)
                    OR (@mobile_phone IS NOT NULL AND c.mobile_phone IS NOT NULL AND c.mobile_phone = @mobile_phone)
                    OR (@home_phone IS NOT NULL AND c.home_phone IS NOT NULL AND c.home_phone = @home_phone)
                    OR  (
                            @email IS NULL
                            AND @business_phone IS NULL
                            AND @mobile_phone IS NULL
                            AND @home_phone IS NULL
                            AND @display_name IS NOT NULL
                            AND c.display_name = @display_name
                        )

            );

        """";
        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("display_name", dto.DisplayName);
        cmd.Parameters.AddWithValue("email", (object?)dto.Email ?? DBNull.Value);
        cmd.Parameters.AddWithValue("business_phone", (object?)dto.BusinessPhone ?? DBNull.Value);
        cmd.Parameters.AddWithValue("mobile_phone", (object?)dto.MobilePhone ?? DBNull.Value);
        cmd.Parameters.AddWithValue("home_phone", (object?)dto.HomePhone ?? DBNull.Value);

        return (bool)(await cmd.ExecuteScalarAsync(ct) ?? false);
    }
}
