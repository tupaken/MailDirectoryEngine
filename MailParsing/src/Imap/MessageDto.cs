using System;
using MailKit;

namespace MailDirectoryEngine.src.Imap;

/// <summary>
/// Lightweight message projection used by IMAP engine read operations.
/// </summary>
/// <param name="Uid">Unique IMAP message identifier.</param>
/// <param name="Titel">Message subject line.</param>
/// <param name="Context">Message body content (HTML preferred, plain text fallback).</param>
internal sealed record MessageDto(
    UniqueId Uid,
    string Titel,
    string Context
);
