namespace MailStorageService.Storage;

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
    /// <returns><see langword="true" /> when the file was stored successfully; otherwise <see langword="false" />.</returns>
    bool Store(string sourcePath, string number);
}
