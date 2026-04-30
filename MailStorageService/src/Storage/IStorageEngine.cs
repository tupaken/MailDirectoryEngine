namespace MailStorageService.Storage;


internal enum StoreStatus
{
    Success,
    DestinationNotFound,
    ShareUnavailable,
    CopyFailed,
    SourceNotFound,
    InvalidTargetFileName,
}


/// <summary>
/// Stores exported mail files in the configured destination share.
/// </summary>
internal interface IStorageEngine
{
    /// <summary>
    /// Copies the given source file into the destination folder for the specified case number.
    /// </summary>
    /// <param name="sourcePath">The container-visible path to the exported mail file.</param>
    /// <param name="number">The case number used to resolve the destination folder.</param>
    /// <param name="targetFileName">Specifies the destination file name without path segments.</param>
    /// <returns>A status value describing whether storage succeeded and, if not, why it failed.</returns>
    public StoreStatus Store(string sourcePath, string number, string targetFileName);
}
