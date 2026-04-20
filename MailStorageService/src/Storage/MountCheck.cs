using System.Diagnostics;

namespace MailStorageService.Storage;

/// <summary>
/// Ensures that the configured SMB/CIFS share is mounted under the local mount path.
/// </summary>
internal sealed class MountCheck : IMountCheck
{
    private readonly string mountPath;
    private readonly bool skipMount;
    private readonly string? sharePath;
    private readonly string? user;
    private readonly string? password;
    private readonly string? domain;
    private readonly string? vers;
    private readonly string? sec;
    private readonly string? uid;
    private readonly string? gid;
    private readonly Func<string, bool> directoryExists;
    private readonly Action<string> createDirectory;
    private readonly Func<string, string, int> runProcess;

    /// <summary>
    /// Initializes mount settings from the current environment variables.
    /// </summary>
    public MountCheck()
        : this(
            mountPath: GetRequiredEnvironmentVariable("MOUNT_PATH"),
            skipMount: IsEnabled(Environment.GetEnvironmentVariable("STORAGE_SKIP_MOUNT")),
            runProcess: RunProcess,
            directoryExists: Directory.Exists,
            createDirectory: static path => Directory.CreateDirectory(path),
            sharePath: Environment.GetEnvironmentVariable("SHARE_PATH"),
            user: Environment.GetEnvironmentVariable("AD_USER"),
            password: Environment.GetEnvironmentVariable("AD_PASSWORD"),
            domain: Environment.GetEnvironmentVariable("AD_DOMAIN"),
            vers: Environment.GetEnvironmentVariable("AD_VERS"),
            sec: Environment.GetEnvironmentVariable("SEC"),
            uid: Environment.GetEnvironmentVariable("UID"),
            gid: Environment.GetEnvironmentVariable("GID"))
    {
    }

    internal MountCheck(
        string mountPath,
        bool skipMount,
        Func<string, string, int> runProcess,
        Func<string, bool>? directoryExists = null,
        Action<string>? createDirectory = null,
        string? sharePath = null,
        string? user = null,
        string? password = null,
        string? domain = null,
        string? vers = null,
        string? sec = null,
        string? uid = null,
        string? gid = null)
    {
        this.mountPath = ValidateRequiredValue(mountPath, "MOUNT_PATH");
        this.skipMount = skipMount;
        this.runProcess = runProcess ?? throw new ArgumentNullException(nameof(runProcess));
        this.directoryExists = directoryExists ?? Directory.Exists;
        this.createDirectory = createDirectory ?? (static path => Directory.CreateDirectory(path));

        if (skipMount)
        {
            return;
        }

        this.sharePath = ValidateRequiredValue(sharePath, "SHARE_PATH");
        this.user = ValidateRequiredValue(user, "AD_USER");
        this.password = ValidateRequiredValue(password, "AD_PASSWORD");
        this.domain = ValidateRequiredValue(domain, "AD_DOMAIN");
        this.vers = ValidateRequiredValue(vers, "AD_VERS");
        this.sec = ValidateRequiredValue(sec, "SEC");
        this.uid = ValidateRequiredValue(uid, "UID");
        this.gid = ValidateRequiredValue(gid, "GID");
    }

    /// <inheritdoc />
    public bool IsMounted()
    {
        if (this.skipMount)
        {
            return this.directoryExists(this.mountPath);
        }

        return this.runProcess("mountpoint", $"-q \"{this.mountPath}\"") == 0;
    }

    /// <inheritdoc />
    public bool Mount()
    {
        if (this.skipMount)
        {
            return this.directoryExists(this.mountPath);
        }

        this.createDirectory(this.mountPath);

        string options =
            $"username={this.user},password={this.password},domain={this.domain},vers={this.vers},sec={this.sec},uid={this.uid},gid={this.gid},noperm";

        return this.runProcess(
            "mount",
            $"-t cifs \"{this.sharePath}\" \"{this.mountPath}\" -o {options}") == 0;
    }

    /// <summary>
    /// Runs a process and returns its exit code.
    /// </summary>
    /// <param name="filename">The executable to start.</param>
    /// <param name="arguments">The command-line arguments.</param>
    /// <returns>The exit code returned by the process.</returns>
    internal static int RunProcess(string filename, string arguments)
    {
        using var process = StartProcess(filename, arguments);
        process.WaitForExit();

        return process.ExitCode;
    }

    /// <summary>
    /// Starts a child process using redirected output streams.
    /// </summary>
    /// <param name="filename">The executable to start.</param>
    /// <param name="arguments">The command-line arguments.</param>
    /// <returns>The started process instance.</returns>
    /// <exception cref="InvalidOperationException">Thrown when the process cannot be started.</exception>
    internal static Process StartProcess(string filename, string arguments)
    {
        var process = Process.Start(new ProcessStartInfo
        {
            FileName = filename,
            Arguments = arguments,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        });

        if (process == null)
        {
            throw new InvalidOperationException($"Unable to start the process: {filename}");
        }

        return process;
    }

    private static string GetRequiredEnvironmentVariable(string name)
    {
        return ValidateRequiredValue(Environment.GetEnvironmentVariable(name), name);
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

    private static bool IsEnabled(string? value)
    {
        var normalized = value?.Trim();

        return normalized is not null
            && (normalized.Equals("true", StringComparison.OrdinalIgnoreCase)
                || normalized.Equals("1", StringComparison.OrdinalIgnoreCase)
                || normalized.Equals("yes", StringComparison.OrdinalIgnoreCase));
    }
}
