using System.Text.Json;
using System.Text.RegularExpressions;
using ContactService.Api.Contracts;
using ContactService.Domain.Abstractions;
using ContactService.Domain.Contacts;

namespace ContactService.Application.Contacts;

internal sealed partial class ContactObservationEngine
{
    private readonly IContactStore _store;
    private readonly IEwsContactClientFactory _factory;
    private readonly IEwsConfigProvider _configProvider;
    private readonly string _accountKey;

    public ContactObservationEngine(
        IContactStore store,
        IEwsContactClientFactory factory,
        IEwsConfigProvider configProvider,
        string accountKey)
    {
        _store = store ?? throw new ArgumentNullException(nameof(store));
        _factory = factory ?? throw new ArgumentNullException(nameof(factory));
        _configProvider = configProvider ?? throw new ArgumentNullException(nameof(configProvider));
        _accountKey = string.IsNullOrWhiteSpace(accountKey)
            ? throw new ArgumentException("Account key is required.", nameof(accountKey))
            : accountKey.Trim();
    }

    public async Task<ContactObservationResultDto> IngestAsync(
        CanonicalContactEnvelopeDto payload,
        CancellationToken ct)
    {
        if (payload is null)
            throw new ArgumentNullException(nameof(payload));

        var dto = CanonicalContactMapper.ToContactDto(payload);
        var phone = SelectPrimaryPhone(payload.Contact.Phones, dto);
        if (phone is null)
            throw new InvalidOperationException("Canonical contact contains no usable phone.");

        var normalizedEmail = NormalizeEmail(dto.Email);
        var phoneDigits = DigitsOnly(phone.Raw);
        var fullName = Clean(dto.DisplayName);
        var company = Clean(dto.Company);
        var evidenceJson = JsonSerializer.Serialize(payload.Evidence);
        var payloadJson = JsonSerializer.Serialize(payload);

        var observation = new ContactObservationRecord(
            Id: 0,
            AccountKey: _accountKey,
            IdentityKey: BuildIdentityKey(normalizedEmail, phoneDigits, fullName, company),
            SourceMessageId: Clean(payload.SourceMessageId),
            FullName: NullIfEmpty(fullName),
            Company: NullIfEmpty(company),
            Email: NullIfEmpty(Clean(dto.Email)),
            NormalizedEmail: NullIfEmpty(normalizedEmail),
            PhoneType: phone.Type,
            PhoneRaw: phone.Raw,
            PhoneDigits: phoneDigits,
            EvidenceJson: evidenceJson,
            PayloadJson: payloadJson,
            Status: "pending",
            Reason: null,
            SeenCount: 1,
            PromotedContactEwsId: null);

        var stored = await _store.UpsertObservationAsync(observation, ct).ConfigureAwait(false);
        var decision = await DecidePromotionAsync(stored, payload.Evidence, ct).ConfigureAwait(false);
        if (!decision.ShouldPromote)
        {
            await _store.MarkObservationStatusAsync(stored.Id, decision.Status, decision.Reason, null, ct)
                .ConfigureAwait(false);
            await _store.InsertChangeLogAsync(
                contactId: null,
                ewsId: null,
                observationId: stored.Id,
                action: decision.Status,
                fieldName: null,
                oldValue: null,
                newValue: stored.PayloadJson,
                sourceMessageId: stored.SourceMessageId,
                reason: decision.Reason,
                ct: ct).ConfigureAwait(false);

            return ToResult(stored, decision.Status, decision.Reason, dto, null);
        }

        var exchangeEngine = new ExchangeContactEngine(_factory, _configProvider, _accountKey);
        var writeResult = await exchangeEngine.UpsertContactAsync(dto, ct, payload.SourceMessageId, stored.Id)
            .ConfigureAwait(false);

        await _store.MarkObservationStatusAsync(stored.Id, "promoted", decision.Reason, writeResult.EwsId, ct)
            .ConfigureAwait(false);

        return ToResult(stored, "promoted", decision.Reason, dto, writeResult.Status);
    }

    private async Task<PromotionDecision> DecidePromotionAsync(
        ContactObservationRecord observation,
        CanonicalContactEvidenceDto? evidence,
        CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(observation.NormalizedEmail) || !EmailRegex().IsMatch(observation.NormalizedEmail))
            return new PromotionDecision(false, "pending", "email_required_for_exchange_promotion");

        var phoneNameConflicts = await _store.CountDistinctNamesForPhoneAsync(
            observation.PhoneDigits,
            observation.FullName,
            ct).ConfigureAwait(false);
        if (phoneNameConflicts > 0)
            return new PromotionDecision(false, "suspicious", "phone_seen_with_different_name");

        var emailNameConflicts = await _store.CountDistinctNamesForEmailAsync(
            observation.NormalizedEmail,
            observation.FullName,
            ct).ConfigureAwait(false);
        if (emailNameConflicts > 0)
            return new PromotionDecision(false, "suspicious", "email_seen_with_different_name");

        var existingEmailContact = await _store.FindExistingContactByEmailAsync(
            observation.NormalizedEmail,
            ct).ConfigureAwait(false);
        if (existingEmailContact is not null && ConflictsWithExistingIdentity(observation, existingEmailContact))
            return new PromotionDecision(false, "suspicious", "existing_email_has_different_identity");

        var existingPhoneContacts = await _store.CountExistingContactsForPhoneAsync(
            observation.PhoneDigits,
            observation.NormalizedEmail,
            ct).ConfigureAwait(false);
        if (existingPhoneContacts > 0)
            return new PromotionDecision(false, "suspicious", "phone_already_belongs_to_existing_contact");

        var hasIdentityText =
            !string.IsNullOrWhiteSpace(observation.FullName) ||
            !string.IsNullOrWhiteSpace(observation.Company);
        if (!hasIdentityText)
            return new PromotionDecision(false, "pending", "name_or_company_required");

        var strongSourceBlock =
            evidence is not null &&
            evidence.EmailInSourceBlock &&
            evidence.PhoneInSourceBlock &&
            (evidence.NameInSourceBlock || evidence.CompanyInSourceBlock);
        var repeatedSameEvidence = observation.SeenCount >= 2;

        if (!strongSourceBlock && !repeatedSameEvidence)
            return new PromotionDecision(false, "pending", "waiting_for_repeated_or_local_context_evidence");

        return new PromotionDecision(true, "promoted", strongSourceBlock ? "strong_local_context" : "repeated_same_identity");
    }

    private static ContactObservationResultDto ToResult(
        ContactObservationRecord observation,
        string status,
        string? reason,
        ContactDto dto,
        string? exchangeStatus)
    {
        return new ContactObservationResultDto(
            Status: status,
            AccountKey: observation.AccountKey,
            ObservationId: observation.Id,
            SeenCount: observation.SeenCount,
            Reason: reason,
            DisplayName: dto.DisplayName,
            Email: dto.Email,
            Phone: dto.BusinessPhone ?? dto.MobilePhone ?? dto.HomePhone ?? dto.BusinessFax,
            ExchangeStatus: exchangeStatus);
    }

    private static PhoneCandidate? SelectPrimaryPhone(
        IReadOnlyList<CanonicalPhoneDto>? phones,
        ContactDto dto)
    {
        if (phones is not null)
        {
            foreach (var phone in phones)
            {
                var value = Clean(phone.Raw);
                if (string.IsNullOrWhiteSpace(value))
                    value = Clean(phone.E164);
                var digits = DigitsOnly(value);
                if (string.IsNullOrWhiteSpace(value) || digits.Length < 6)
                    continue;

                return new PhoneCandidate(NormalizePhoneType(phone.Type), value);
            }
        }

        foreach (var fallback in new[] { dto.BusinessPhone, dto.MobilePhone, dto.HomePhone, dto.BusinessFax })
        {
            var value = Clean(fallback);
            if (!string.IsNullOrWhiteSpace(value) && DigitsOnly(value).Length >= 6)
                return new PhoneCandidate("business", value);
        }

        return null;
    }

    private static string BuildIdentityKey(string email, string phoneDigits, string fullName, string company)
    {
        return string.Join(
            "|",
            NormalizeEmail(email),
            phoneDigits,
            NormalizeName(fullName),
            NormalizeName(company));
    }

    private static bool ConflictsWithExistingIdentity(
        ContactObservationRecord observation,
        ExistingContactIdentity existing)
    {
        var incomingName = NormalizeName(observation.FullName);
        var existingName = NormalizeName(existing.FullName);
        if (string.IsNullOrWhiteSpace(existingName))
            existingName = NormalizeName(existing.DisplayName);

        if (!string.IsNullOrWhiteSpace(incomingName) &&
            !string.IsNullOrWhiteSpace(existingName) &&
            incomingName != existingName)
        {
            return true;
        }

        var incomingCompany = NormalizeName(observation.Company);
        var existingCompany = NormalizeName(existing.Company);
        return !string.IsNullOrWhiteSpace(incomingCompany) &&
               !string.IsNullOrWhiteSpace(existingCompany) &&
               incomingCompany != existingCompany;
    }

    private static string NormalizeEmail(string? value)
    {
        return Clean(value).ToLowerInvariant();
    }

    private static string NormalizeName(string? value)
    {
        return Clean(value).ToLowerInvariant();
    }

    private static string NormalizePhoneType(string? value)
    {
        var cleaned = Clean(value).ToLowerInvariant();
        return string.IsNullOrWhiteSpace(cleaned) ? "other" : cleaned;
    }

    private static string DigitsOnly(string? value)
    {
        return string.Concat(Clean(value).Where(char.IsDigit));
    }

    private static string Clean(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim();
    }

    private static string? NullIfEmpty(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value;
    }

    [GeneratedRegex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", RegexOptions.IgnoreCase)]
    private static partial Regex EmailRegex();

    private sealed record PhoneCandidate(string Type, string Raw);
    private sealed record PromotionDecision(bool ShouldPromote, string Status, string Reason);
}
