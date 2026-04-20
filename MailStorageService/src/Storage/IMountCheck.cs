namespace MailStorageService.Storage;

/// <summary>
/// Verifies whether the configured share is mounted and mounts it when required.
/// </summary>
internal interface IMountCheck
{
    /// <summary>
    /// Determines whether the configured mount path is currently available.
    /// </summary>
    /// <returns><see langword="true" /> when the share is mounted; otherwise <see langword="false" />.</returns>
    bool IsMounted();

    /// <summary>
    /// Attempts to mount the configured share.
    /// </summary>
    /// <returns><see langword="true" /> when the mount succeeded; otherwise <see langword="false" />.</returns>
    bool Mount();
}
