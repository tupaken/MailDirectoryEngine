using MailStorageService.Storage;

namespace MailStorageService.Tests;

public class StorageEngineTests
{
    /// <summary>
    /// Verifies that storage reports share unavailability after all mount retries are exhausted.
    /// </summary>
    [Fact]
    public void Store_ReturnsShareUnavailable_WhenShareCannotBeMounted()
    {
        var mountCheck = new FakeMountCheck(false);
        var delayCalls = 0;
        var engine = new StorageEngine(
            mountCheck,
            mountPath: "ignored",
            directory2: "Dokumente",
            directory3: "Bewerbungen",
            copyWithRsync: static (_, _) => 0,
            delay: _ => delayCalls++);

        var result = engine.Store("/mail-export/message.eml", "12345");

        Assert.Equal(StoreStatus.ShareUnavailable, result);
        Assert.Equal(5, mountCheck.MountCallCount);
        Assert.Equal(5, delayCalls);
    }

    /// <summary>
    /// Verifies that the engine mounts once and then stores the file when the share becomes available.
    /// </summary>
    [Fact]
    public void Store_MountsShare_WhenInitiallyNotMounted()
    {
        var root = CreateTempDirectory();

        try
        {
            var targetDirectory = CreateMatchingDirectoryTree(root, "12345");
            var sourcePath = CreateSourceFile(root);
            var mountCheck = new FakeMountCheck(false, true);
            var destinations = new List<string>();
            var engine = new StorageEngine(
                mountCheck,
                mountPath: root,
                directory2: "Dokumente",
                directory3: "Bewerbungen",
                copyWithRsync: (_, destinationPath) =>
                {
                    destinations.Add(destinationPath);
                    return 0;
                },
                delay: _ => { });

            var result = engine.Store(sourcePath, "12345");

            Assert.Equal(StoreStatus.Success, result);
            Assert.Equal(1, mountCheck.MountCallCount);
            Assert.Equal(targetDirectory, Assert.Single(destinations));
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that storage reports a missing destination when no matching target folder exists.
    /// </summary>
    [Fact]
    public void Store_ReturnsDestinationNotFound_WhenDestinationCannotBeResolved()
    {
        var root = CreateTempDirectory();

        try
        {
            var sourcePath = CreateSourceFile(root);
            var engine = new StorageEngine(
                new FakeMountCheck(true),
                mountPath: root,
                directory2: "Dokumente",
                directory3: "Bewerbungen",
                copyWithRsync: static (_, _) => 0,
                delay: _ => { });

            var result = engine.Store(sourcePath, "12345");

            Assert.Equal(StoreStatus.DestinationNotFound, result);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that storage reports a missing source file before destination lookup or copying.
    /// </summary>
    [Fact]
    public void Store_ReturnsSourceNotFound_WhenSourceFileIsMissing()
    {
        var root = CreateTempDirectory();

        try
        {
            CreateMatchingDirectoryTree(root, "12345");
            var engine = new StorageEngine(
                new FakeMountCheck(true),
                mountPath: root,
                directory2: "Dokumente",
                directory3: "Bewerbungen",
                copyWithRsync: static (_, _) => 0,
                delay: _ => { });

            var result = engine.Store(Path.Combine(root, "missing.eml"), "12345");

            Assert.Equal(StoreStatus.SourceNotFound, result);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that the engine resolves the normalized target folder and copies the file immediately.
    /// </summary>
    [Fact]
    public void Store_UsesResolvedTargetDirectory_WhenCopySucceedsImmediately()
    {
        var root = CreateTempDirectory();

        try
        {
            var targetDirectory = CreateMatchingDirectoryTree(root, "12345");
            var tempSourcePath = CreateSourceFile(root);
            string? sourcePath = null;
            string? destinationPath = null;
            var engine = new StorageEngine(
                new FakeMountCheck(true),
                mountPath: root,
                directory2: "Dokumente",
                directory3: "Bewerbungen",
                copyWithRsync: (currentSourcePath, currentDestinationPath) =>
                {
                    sourcePath = currentSourcePath;
                    destinationPath = currentDestinationPath;
                    return 0;
                },
                delay: _ => { });

            var result = engine.Store(tempSourcePath, "12345");

            Assert.Equal(StoreStatus.Success, result);
            Assert.Equal(tempSourcePath, sourcePath);
            Assert.Equal(targetDirectory, destinationPath);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that failed rsync attempts are retried until one succeeds.
    /// </summary>
    [Fact]
    public void Store_RetriesCopy_WhenRsyncEventuallySucceeds()
    {
        var root = CreateTempDirectory();

        try
        {
            CreateMatchingDirectoryTree(root, "12345");
            var sourcePath = CreateSourceFile(root);
            var exitCodes = new Queue<int>(new[] { 23, 23, 0 });
            var delayCalls = 0;
            var engine = new StorageEngine(
                new FakeMountCheck(true),
                mountPath: root,
                directory2: "Dokumente",
                directory3: "Bewerbungen",
                copyWithRsync: (_, _) => exitCodes.Dequeue(),
                delay: _ => delayCalls++);

            var result = engine.Store(sourcePath, "12345");

            Assert.Equal(StoreStatus.Success, result);
            Assert.Empty(exitCodes);
            Assert.Equal(1, delayCalls);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that storage reports copy failure after the initial rsync attempt and all retries fail.
    /// </summary>
    [Fact]
    public void Store_ReturnsCopyFailed_WhenAllCopyAttemptsFail()
    {
        var root = CreateTempDirectory();

        try
        {
            CreateMatchingDirectoryTree(root, "12345");
            var sourcePath = CreateSourceFile(root);
            var attempts = 0;
            var engine = new StorageEngine(
                new FakeMountCheck(true),
                mountPath: root,
                directory2: "Dokumente",
                directory3: "Bewerbungen",
                copyWithRsync: (_, _) =>
                {
                    attempts++;
                    return 23;
                },
                delay: _ => { });

            var result = engine.Store(sourcePath, "12345");

            Assert.Equal(StoreStatus.CopyFailed, result);
            Assert.Equal(6, attempts);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    /// <summary>
    /// Verifies that environment-backed construction validates required folder configuration.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenDirectory3IsMissing()
    {
        using var scope = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            ["MOUNT_PATH"] = "/mounted-share",
            ["DIRECTORY2"] = "Dokumente",
            ["DIRECTORY3"] = null,
            ["STORAGE_SKIP_MOUNT"] = "true"
        });

        var exception = Assert.Throws<InvalidOperationException>(() => new StorageEngine());

        Assert.Equal("DIRECTORY3 is missing from the environment", exception.Message);
    }

    private static string CreateSourceFile(string root)
    {
        var path = Path.Combine(root, "message.eml");
        File.WriteAllText(path, "mail");
        return path;
    }

    private static string CreateMatchingDirectoryTree(string root, string number)
    {
        var level1 = Directory.CreateDirectory(Path.Combine(root, $"{number}-Akte"));
        var level2 = Directory.CreateDirectory(Path.Combine(level1.FullName, "01_Dokumente"));
        var otherDirectory = Directory.CreateDirectory(Path.Combine(level2.FullName, "Zwischenablage"));
        _ = otherDirectory;

        return Directory.CreateDirectory(Path.Combine(level2.FullName, "Bewerbungen & Lebenslaeufe")).FullName;
    }

    private static string CreateTempDirectory()
    {
        var path = Path.Combine(
            Path.GetTempPath(),
            "MailStorageService.Tests",
            Guid.NewGuid().ToString("N"));

        Directory.CreateDirectory(path);
        return path;
    }
}
