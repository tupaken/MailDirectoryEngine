using System;
using MailKit;

namespace MailDirectoryEngine.src.Imap;

internal sealed record MessageDto(
    UniqueId Uid,
    string Titel,
    string Context
);