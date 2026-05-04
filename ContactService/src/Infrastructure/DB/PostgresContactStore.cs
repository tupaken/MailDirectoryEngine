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
    public async Task<string?> ExistsAsync(ContactDto dto, CancellationToken ct)
    {
        const string sql = """" 
            SELECT c.ews_id 
            FROM contacts c
            WHERE
                @email IS NOT NULL
                AND c.email IS NOT NULL
                AND LOWER(BTRIM(c.email)) = @email
            LIMIT 1;
        """";

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.Add("email", NpgsqlDbType.Text).Value = NormalizeEmail(dto.Email) is { Length: > 0 } email
            ? email
            : DBNull.Value;

        var result= await cmd.ExecuteScalarAsync(ct);
        return result as string;
    }

    public async Task<long> InsertAsync(ContactDto dto, string ewsId ,string? sourceMessageId, CancellationToken ct)
    {
        const string sql = """
        INSERT INTO contacts (
            source_message_id, display_name, full_name, given_name, middle_name, surname,
            company_name, job_title, file_as, email, website,
            business_phone, home_phone, mobile_phone, business_fax,
            notes, emails, phone_numbers, addresses, ews_id, normalized_email
        )
        VALUES (
            @source_message_id, @display_name, @full_name, @given_name, @middle_name, @surname,
            @company_name, @job_title, @file_as, @email, @website,
            @business_phone, @home_phone, @mobile_phone, @business_fax,
            @notes, CAST(@emails AS jsonb), CAST(@phone_numbers AS jsonb), CAST(@addresses AS jsonb), @ews_id, @normalized_email
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
        cmd.Parameters.AddWithValue("ews_id",ewsId);
        cmd.Parameters.AddWithValue("normalized_email", NormalizeEmail(dto.Email) is { Length: > 0 } email
            ? email
            : DBNull.Value);

        var id = await cmd.ExecuteScalarAsync(ct);
        var contactId = Convert.ToInt64(id);
        await RefreshContactLookupAsync(contactId, dto, ct).ConfigureAwait(false);
        return contactId;
    }

    public async Task<long?> FindContactIdByEwsIdAsync(string ewsId, CancellationToken ct)
    {
        const string sql = "SELECT id FROM contacts WHERE ews_id = @ews_id LIMIT 1;";

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("ews_id", ewsId);
        var id = await cmd.ExecuteScalarAsync(ct).ConfigureAwait(false);
        return id is null ? null : Convert.ToInt64(id);
    }

    public async Task UpdateFromPromotedObservationAsync(
        ContactDto dto,
        string ewsId,
        string? sourceMessageId,
        CancellationToken ct)
    {
        const string sql = """
        UPDATE contacts
        SET
            source_message_id = COALESCE(NULLIF(source_message_id, ''), @source_message_id),
            full_name = COALESCE(NULLIF(full_name, ''), @full_name),
            given_name = COALESCE(NULLIF(given_name, ''), @given_name),
            surname = COALESCE(NULLIF(surname, ''), @surname),
            company_name = COALESCE(NULLIF(company_name, ''), @company_name),
            website = COALESCE(NULLIF(website, ''), @website),
            business_phone = CASE WHEN @business_phone IS NOT NULL THEN @business_phone ELSE business_phone END,
            home_phone = CASE WHEN @home_phone IS NOT NULL THEN @home_phone ELSE home_phone END,
            mobile_phone = CASE WHEN @mobile_phone IS NOT NULL THEN @mobile_phone ELSE mobile_phone END,
            business_fax = CASE WHEN @business_fax IS NOT NULL THEN @business_fax ELSE business_fax END,
            emails = CASE WHEN emails = '{}'::jsonb THEN CAST(@emails AS jsonb) ELSE emails END,
            phone_numbers = CASE WHEN phone_numbers = '{}'::jsonb THEN CAST(@phone_numbers AS jsonb) ELSE phone_numbers END,
            addresses = CASE WHEN addresses = '{}'::jsonb THEN CAST(@addresses AS jsonb) ELSE addresses END,
            normalized_email = COALESCE(NULLIF(normalized_email, ''), @normalized_email)
        WHERE ews_id = @ews_id;
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("source_message_id", (object?)sourceMessageId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("full_name", dto.DisplayName);
        cmd.Parameters.AddWithValue("given_name", (object?)dto.GivenName ?? DBNull.Value);
        cmd.Parameters.AddWithValue("surname", (object?)dto.Surname ?? DBNull.Value);
        cmd.Parameters.AddWithValue("company_name", (object?)dto.Company ?? DBNull.Value);
        cmd.Parameters.AddWithValue("website", (object?)dto.WebPage ?? DBNull.Value);
        cmd.Parameters.AddWithValue("business_phone", (object?)dto.BusinessPhone ?? DBNull.Value);
        cmd.Parameters.AddWithValue("home_phone", (object?)dto.HomePhone ?? DBNull.Value);
        cmd.Parameters.AddWithValue("mobile_phone", (object?)dto.MobilePhone ?? DBNull.Value);
        cmd.Parameters.AddWithValue("business_fax", (object?)dto.BusinessFax ?? DBNull.Value);
        cmd.Parameters.AddWithValue("emails", JsonSerializer.Serialize(dto.Emails));
        cmd.Parameters.AddWithValue("phone_numbers", JsonSerializer.Serialize(dto.PhoneNumbers));
        cmd.Parameters.AddWithValue("addresses", JsonSerializer.Serialize(dto.Addresses));
        cmd.Parameters.AddWithValue("ews_id", ewsId);
        cmd.Parameters.AddWithValue("normalized_email", NormalizeEmail(dto.Email) is { Length: > 0 } email
            ? email
            : DBNull.Value);

        await cmd.ExecuteNonQueryAsync(ct).ConfigureAwait(false);
        var contactId = await FindContactIdByEwsIdAsync(ewsId, ct).ConfigureAwait(false);
        if (contactId is not null)
            await RefreshContactLookupAsync(contactId.Value, dto, ct).ConfigureAwait(false);
    }

    public async Task<ContactObservationRecord> UpsertObservationAsync(
        ContactObservationRecord observation,
        CancellationToken ct)
    {
        const string sql = """
        INSERT INTO contact_observations (
            account_key, source_message_id, identity_key, full_name, company_name,
            email, normalized_email, phone_type, phone_raw, phone_digits,
            evidence, payload, status, reason, promoted_contact_ews_id
        )
        VALUES (
            @account_key, @source_message_id, @identity_key, @full_name, @company_name,
            @email, @normalized_email, @phone_type, @phone_raw, @phone_digits,
            CAST(@evidence AS jsonb), CAST(@payload AS jsonb), @status, @reason, @promoted_contact_ews_id
        )
        ON CONFLICT (account_key, identity_key)
        DO UPDATE SET
            source_message_id = COALESCE(EXCLUDED.source_message_id, contact_observations.source_message_id),
            evidence = EXCLUDED.evidence,
            payload = EXCLUDED.payload,
            seen_count = contact_observations.seen_count + 1,
            last_seen_at = NOW()
        RETURNING id, seen_count, status, reason, promoted_contact_ews_id;
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("account_key", observation.AccountKey);
        cmd.Parameters.AddWithValue("source_message_id", (object?)observation.SourceMessageId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("identity_key", observation.IdentityKey);
        cmd.Parameters.AddWithValue("full_name", (object?)observation.FullName ?? DBNull.Value);
        cmd.Parameters.AddWithValue("company_name", (object?)observation.Company ?? DBNull.Value);
        cmd.Parameters.AddWithValue("email", (object?)observation.Email ?? DBNull.Value);
        cmd.Parameters.AddWithValue("normalized_email", (object?)observation.NormalizedEmail ?? DBNull.Value);
        cmd.Parameters.AddWithValue("phone_type", observation.PhoneType);
        cmd.Parameters.AddWithValue("phone_raw", observation.PhoneRaw);
        cmd.Parameters.AddWithValue("phone_digits", observation.PhoneDigits);
        cmd.Parameters.AddWithValue("evidence", observation.EvidenceJson);
        cmd.Parameters.AddWithValue("payload", observation.PayloadJson);
        cmd.Parameters.AddWithValue("status", observation.Status);
        cmd.Parameters.AddWithValue("reason", (object?)observation.Reason ?? DBNull.Value);
        cmd.Parameters.AddWithValue("promoted_contact_ews_id", (object?)observation.PromotedContactEwsId ?? DBNull.Value);

        await using var reader = await cmd.ExecuteReaderAsync(ct).ConfigureAwait(false);
        if (!await reader.ReadAsync(ct).ConfigureAwait(false))
            throw new InvalidOperationException("Contact observation upsert returned no row.");

        return observation with
        {
            Id = reader.GetInt64(0),
            SeenCount = reader.GetInt32(1),
            Status = reader.GetString(2),
            Reason = reader.IsDBNull(3) ? null : reader.GetString(3),
            PromotedContactEwsId = reader.IsDBNull(4) ? null : reader.GetString(4)
        };
    }

    public async Task MarkObservationStatusAsync(
        long observationId,
        string status,
        string? reason,
        string? promotedContactEwsId,
        CancellationToken ct)
    {
        const string sql = """
        UPDATE contact_observations
        SET status = @status,
            reason = @reason,
            promoted_contact_ews_id = @promoted_contact_ews_id,
            last_seen_at = NOW()
        WHERE id = @id;
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("id", observationId);
        cmd.Parameters.AddWithValue("status", status);
        cmd.Parameters.AddWithValue("reason", (object?)reason ?? DBNull.Value);
        cmd.Parameters.AddWithValue("promoted_contact_ews_id", (object?)promotedContactEwsId ?? DBNull.Value);

        await cmd.ExecuteNonQueryAsync(ct).ConfigureAwait(false);
    }

    public async Task<int> CountDistinctNamesForPhoneAsync(string phoneDigits, string? fullName, CancellationToken ct)
    {
        const string sql = """
        SELECT COUNT(DISTINCT LOWER(BTRIM(full_name)))
        FROM contact_observations
        WHERE phone_digits = @phone_digits
          AND full_name IS NOT NULL
          AND BTRIM(full_name) <> ''
          AND (@full_name IS NULL OR LOWER(BTRIM(full_name)) <> @full_name);
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("phone_digits", phoneDigits);
        cmd.Parameters.Add("full_name", NpgsqlDbType.Text).Value = NormalizeName(fullName) is { Length: > 0 } name
            ? name
            : DBNull.Value;

        var count = await cmd.ExecuteScalarAsync(ct).ConfigureAwait(false);
        return Convert.ToInt32(count);
    }

    public async Task<int> CountDistinctNamesForEmailAsync(string normalizedEmail, string? fullName, CancellationToken ct)
    {
        const string sql = """
        SELECT COUNT(DISTINCT LOWER(BTRIM(full_name)))
        FROM contact_observations
        WHERE normalized_email = @normalized_email
          AND full_name IS NOT NULL
          AND BTRIM(full_name) <> ''
          AND (@full_name IS NULL OR LOWER(BTRIM(full_name)) <> @full_name);
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("normalized_email", normalizedEmail);
        cmd.Parameters.Add("full_name", NpgsqlDbType.Text).Value = NormalizeName(fullName) is { Length: > 0 } name
            ? name
            : DBNull.Value;

        var count = await cmd.ExecuteScalarAsync(ct).ConfigureAwait(false);
        return Convert.ToInt32(count);
    }

    public async Task<ExistingContactIdentity?> FindExistingContactByEmailAsync(
        string normalizedEmail,
        CancellationToken ct)
    {
        const string sql = """
        SELECT id, ews_id, display_name, full_name, company_name, normalized_email
        FROM contacts
        WHERE normalized_email = @normalized_email
        LIMIT 1;
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("normalized_email", normalizedEmail);

        await using var reader = await cmd.ExecuteReaderAsync(ct).ConfigureAwait(false);
        if (!await reader.ReadAsync(ct).ConfigureAwait(false))
            return null;

        return new ExistingContactIdentity(
            Id: reader.GetInt64(0),
            EwsId: reader.GetString(1),
            DisplayName: reader.GetString(2),
            FullName: reader.IsDBNull(3) ? null : reader.GetString(3),
            Company: reader.IsDBNull(4) ? null : reader.GetString(4),
            NormalizedEmail: reader.IsDBNull(5) ? null : reader.GetString(5));
    }

    public async Task<int> CountExistingContactsForPhoneAsync(
        string phoneDigits,
        string? normalizedEmail,
        CancellationToken ct)
    {
        const string sql = """
        SELECT COUNT(DISTINCT c.id)
        FROM contact_phone_index p
        JOIN contacts c ON c.id = p.contact_id
        WHERE p.phone_digits = @phone_digits
          AND (
              @normalized_email IS NULL
              OR c.normalized_email IS NULL
              OR c.normalized_email <> @normalized_email
          );
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("phone_digits", phoneDigits);
        cmd.Parameters.Add("normalized_email", NpgsqlDbType.Text).Value =
            NormalizeEmail(normalizedEmail) is { Length: > 0 } email ? email : DBNull.Value;

        var count = await cmd.ExecuteScalarAsync(ct).ConfigureAwait(false);
        return Convert.ToInt32(count);
    }

    public async Task InsertChangeLogAsync(
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
        const string sql = """
        INSERT INTO contact_change_log (
            contact_id, ews_id, observation_id, action, field_name,
            old_value, new_value, source_message_id, reason
        )
        VALUES (
            @contact_id, @ews_id, @observation_id, @action, @field_name,
            @old_value, @new_value, @source_message_id, @reason
        );
        """;

        await using var cmd = _dataSource.CreateCommand(sql);
        cmd.Parameters.AddWithValue("contact_id", (object?)contactId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("ews_id", (object?)ewsId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("observation_id", (object?)observationId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("action", action);
        cmd.Parameters.AddWithValue("field_name", (object?)fieldName ?? DBNull.Value);
        cmd.Parameters.AddWithValue("old_value", (object?)oldValue ?? DBNull.Value);
        cmd.Parameters.AddWithValue("new_value", (object?)newValue ?? DBNull.Value);
        cmd.Parameters.AddWithValue("source_message_id", (object?)sourceMessageId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("reason", (object?)reason ?? DBNull.Value);

        await cmd.ExecuteNonQueryAsync(ct).ConfigureAwait(false);
    }

    private async Task RefreshContactLookupAsync(long contactId, ContactDto dto, CancellationToken ct)
    {
        const string deleteSql = "DELETE FROM contact_phone_index WHERE contact_id = @contact_id;";
        await using (var deleteCmd = _dataSource.CreateCommand(deleteSql))
        {
            deleteCmd.Parameters.AddWithValue("contact_id", contactId);
            await deleteCmd.ExecuteNonQueryAsync(ct).ConfigureAwait(false);
        }

        const string insertSql = """
        INSERT INTO contact_phone_index (contact_id, phone_digits, phone_raw, source_key)
        VALUES (@contact_id, @phone_digits, @phone_raw, @source_key)
        ON CONFLICT DO NOTHING;
        """;

        var phones = CollectPhones(dto);
        foreach (var phone in phones)
        {
            await using var insertCmd = _dataSource.CreateCommand(insertSql);
            insertCmd.Parameters.AddWithValue("contact_id", contactId);
            insertCmd.Parameters.AddWithValue("phone_digits", phone.PhoneDigits);
            insertCmd.Parameters.AddWithValue("phone_raw", phone.PhoneRaw);
            insertCmd.Parameters.AddWithValue("source_key", phone.SourceKey);
            await insertCmd.ExecuteNonQueryAsync(ct).ConfigureAwait(false);
        }
    }

    private static IReadOnlyList<ContactPhoneLookup> CollectPhones(ContactDto dto)
    {
        var phones = new List<ContactPhoneLookup>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        void Add(string sourceKey, string? raw)
        {
            if (string.IsNullOrWhiteSpace(raw))
                return;

            var digits = DigitsOnly(raw);
            if (string.IsNullOrWhiteSpace(digits))
                return;

            var key = $"{sourceKey}|{digits}";
            if (!seen.Add(key))
                return;

            phones.Add(new ContactPhoneLookup(sourceKey, raw.Trim(), digits));
        }

        Add("business_phone", dto.BusinessPhone);
        Add("home_phone", dto.HomePhone);
        Add("mobile_phone", dto.MobilePhone);
        Add("business_fax", dto.BusinessFax);

        if (dto.PhoneNumbers is not null)
        {
            foreach (var kv in dto.PhoneNumbers)
                Add(kv.Key, kv.Value);
        }

        return phones;
    }

    private static string NormalizeEmail(string? email)
    {
        return string.IsNullOrWhiteSpace(email) ? string.Empty : email.Trim().ToLowerInvariant();
    }

    private static string NormalizeName(string? name)
    {
        return string.IsNullOrWhiteSpace(name) ? string.Empty : name.Trim().ToLowerInvariant();
    }

    private static string DigitsOnly(string value)
    {
        return string.Concat(value.Where(char.IsDigit));
    }

    private sealed record ContactPhoneLookup(string SourceKey, string PhoneRaw, string PhoneDigits);
}
