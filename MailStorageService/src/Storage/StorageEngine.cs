namespace MailStorageService.Storage;

/// <summary>
/// Resolves the destination directory on the mounted share and copies exported mail files into it.
/// </summary>
internal sealed class StorageEngine : IStorageEngine
{
    private readonly IMountCheck check;
    private readonly string mountPath;
    private readonly string directory2;
    private readonly string directory3;
    private readonly Func<string, string, int> copyWithRsync;
    private readonly Action<TimeSpan> delay;

    /// <summary>
    /// Initializes storage settings from environment variables.
    /// </summary>
    public StorageEngine()
        : this(
            check: new MountCheck(),
            mountPath: GetRequiredEnvironmentVariable("MOUNT_PATH"),
            directory2: GetRequiredEnvironmentVariable("DIRECTORY2"),
            directory3: GetRequiredEnvironmentVariable("DIRECTORY3"),
            copyWithRsync: DefaultCopyWithRsync,
            delay: static duration => Thread.Sleep(duration))
    {
    }

    internal StorageEngine(
        IMountCheck check,
        string mountPath,
        string directory2,
        string directory3,
        Func<string, string, int>? copyWithRsync = null,
        Action<TimeSpan>? delay = null)
    {
        this.check = check ?? throw new ArgumentNullException(nameof(check));
        this.mountPath = ValidateRequiredValue(mountPath, "MOUNT_PATH");
        this.directory2 = ValidateRequiredValue(directory2, "DIRECTORY2");
        this.directory3 = ValidateRequiredValue(directory3, "DIRECTORY3");
        this.copyWithRsync = copyWithRsync ?? DefaultCopyWithRsync;
        this.delay = delay ?? (static duration => Thread.Sleep(duration));
    }

    /// <inheritdoc />
    public bool Store(string sourcePath, string number)
    {
        var isMounted = this.check.IsMounted();

        if (!isMounted)
        {
            const int maxMountRetries = 5;

            for (int i = 0; i < maxMountRetries && !isMounted; i++)
            {
                this.check.Mount();
                isMounted = this.check.IsMounted();
                this.delay(TimeSpan.FromSeconds(1));
            }

            if (!isMounted)
            {
                return false;
            }
        }

        var destinationPath = this.FindPath(number);

        if (destinationPath == null)
        {
            return false;
        }

        if (this.copyWithRsync(sourcePath, destinationPath) == 0)
        {
            return true;
        }

        return CopyWithRetry(sourcePath, destinationPath);
    }

    /// <summary>
    /// Finds the final destination directory for the given case number.
    /// </summary>
    /// <param name="number">The case number prefix used at the top-level share folder.</param>
    /// <returns>The resolved destination path, or <see langword="null" /> when no match exists.</returns>
    internal string? FindPath(string number)
    {
        var level1 = Directory.EnumerateDirectories(this.mountPath, number + "*");

        foreach (var d1 in level1)
        {
            var d2 = Directory.EnumerateDirectories(d1, $"*{this.directory2}*", SearchOption.AllDirectories)
                .FirstOrDefault();

            if (d2 == null)
            {
                continue;
            }

            var d3 = Directory.EnumerateDirectories(d2, "*", SearchOption.AllDirectories)
                .FirstOrDefault(path => Normalize(Path.GetFileName(path)).Contains(Normalize(this.directory3)));

            if (d3 != null)
            {
                return d3;
            }
        }

        return null;
    }

    private static int DefaultCopyWithRsync(string sourcePath, string destinationPath)
    {
        return MountCheck.RunProcess(
            "rsync",
            $"-av --partial --inplace \"{sourcePath}\" \"{destinationPath}\"");
    }

    private bool CopyWithRetry(string sourcePath, string destinationPath)
    {
        const int maxRetries = 5;

        for (int i = 1; i <= maxRetries; i++)
        {
            Console.WriteLine($"Try {i}");

            if (this.copyWithRsync(sourcePath, destinationPath) == 0)
            {
                Console.WriteLine("Copying successful");
                return true;
            }

            Console.WriteLine("Copy failed, retrying...");
            this.delay(TimeSpan.FromSeconds(5));
        }

        Console.WriteLine("Copy failed completely");
        return false;
    }

    private static string GetRequiredEnvironmentVariable(string name)
    {
        return ValidateRequiredValue(
            Environment.GetEnvironmentVariable(name),
            name);
    }

    private static string ValidateRequiredValue(string? value, string name)
    {
        var normalized = value?.Trim();

        if (string.IsNullOrWhiteSpace(normalized))
        {
            throw new InvalidOperationException($"{name} is missing from the environment");
        }

        return normalized;
    }

    private static string Normalize(string input)
    {
        return new string(
            input
                .ToLowerInvariant()
                .Where(char.IsLetterOrDigit)
                .ToArray());
    }
}
