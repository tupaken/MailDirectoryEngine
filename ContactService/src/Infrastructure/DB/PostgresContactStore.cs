using ContactService.Domain.Abstractions;
using ContactService.Domain.Contacts;
using Npgsql;
using NpgsqlTypes;
using System.Text.Json;
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
                    OR ((@business_phone IS NOT NULL AND c.business_phone IS NOT NULL AND c.business_phone = @business_phone) 
                        AND @display_name = c.display_name)
                    OR ((@mobile_phone IS NOT NULL AND c.mobile_phone IS NOT NULL AND c.mobile_phone = @mobile_phone)
                        AND @display_name = c.display_name)
                    OR ((@home_phone IS NOT NULL AND c.home_phone IS NOT NULL AND c.home_phone = @home_phone)
                        AND @display_name = c.display_name)
                    OR
                        c.display_name = @display_name


            );

        """";
        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.Add("display_name", NpgsqlDbType.Text).Value = dto.DisplayName;
        cmd.Parameters.Add("email", NpgsqlDbType.Text).Value = (object?)dto.Email ?? DBNull.Value;
        cmd.Parameters.Add("business_phone", NpgsqlDbType.Text).Value = (object?)dto.BusinessPhone ?? DBNull.Value;
        cmd.Parameters.Add("mobile_phone", NpgsqlDbType.Text).Value = (object?)dto.MobilePhone ?? DBNull.Value;
        cmd.Parameters.Add("home_phone", NpgsqlDbType.Text).Value = (object?)dto.HomePhone ?? DBNull.Value;

        return (bool)(await cmd.ExecuteScalarAsync(ct) ?? false);
    }

    public async Task<long> InsertAsync(ContactDto dto, string? sourceMessageId, CancellationToken ct)
    {
        const string sql = """
        INSERT INTO contacts (
            source_message_id, display_name, full_name, given_name, middle_name, surname,
            company_name, job_title, file_as, email, website,
            business_phone, home_phone, mobile_phone, business_fax,
            notes, emails, phone_numbers, addresses
        )
        VALUES (
            @source_message_id, @display_name, @full_name, @given_name, @middle_name, @surname,
            @company_name, @job_title, @file_as, @email, @website,
            @business_phone, @home_phone, @mobile_phone, @business_fax,
            @notes, CAST(@emails AS jsonb), CAST(@phone_numbers AS jsonb), CAST(@addresses AS jsonb)
        )
        RETURNING id;
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("source_message_id", (object?)sourceMessageId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("display_name", dto.DisplayName);
        cmd.Parameters.AddWithValue("full_name", dto.DisplayName);
        cmd.Parameters.AddWithValue("given_name", (object?)dto.GivenName ?? DBNull.Value);
        cmd.Parameters.AddWithValue("middle_name", (object?)dto.MiddleName ?? DBNull.Value);
        cmd.Parameters.AddWithValue("surname", (object?)dto.Surname ?? DBNull.Value);
        cmd.Parameters.AddWithValue("company_name", (object?)dto.Company ?? DBNull.Value);
        cmd.Parameters.AddWithValue("job_title", (object?)dto.JobTitle ?? DBNull.Value);
        cmd.Parameters.AddWithValue("file_as", (object?)dto.FileAs ?? DBNull.Value);
        cmd.Parameters.AddWithValue("email", (object?)dto.Email ?? DBNull.Value);
        cmd.Parameters.AddWithValue("website", (object?)dto.WebPage ?? DBNull.Value);
        cmd.Parameters.AddWithValue("business_phone", (object?)dto.BusinessPhone ?? DBNull.Value);
        cmd.Parameters.AddWithValue("home_phone", (object?)dto.HomePhone ?? DBNull.Value);
        cmd.Parameters.AddWithValue("mobile_phone", (object?)dto.MobilePhone ?? DBNull.Value);
        cmd.Parameters.AddWithValue("business_fax", (object?)dto.BusinessFax ?? DBNull.Value);
        cmd.Parameters.AddWithValue("notes", (object?)dto.Notes ?? DBNull.Value);
        cmd.Parameters.AddWithValue("emails", JsonSerializer.Serialize(dto.Emails));
        cmd.Parameters.AddWithValue("phone_numbers", JsonSerializer.Serialize(dto.PhoneNumbers));
        cmd.Parameters.AddWithValue("addresses", JsonSerializer.Serialize(dto.Addresses));

        var id = await cmd.ExecuteScalarAsync(ct);
        return Convert.ToInt64(id);
    }
}
