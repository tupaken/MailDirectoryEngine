using System;
using System.Diagnostics;
using System.IO;

namespace MailStorageService.Storage;

internal sealed class MountCheck : IMountCheck
{
    private readonly string MountPath;
    private readonly bool SkipMount;
    private readonly string? SharePath;
    private readonly string? User;
    private readonly string? Password;
    private readonly string? Domain;
    private readonly string? Vers;
    private readonly string? Sec;
    private readonly string? Uid;
    private readonly string? Gid;

    public MountCheck()
    {
        this.MountPath = GetRequiredEnvironmentVariable("MOUNT_PATH");
        this.SkipMount = IsEnabled(Environment.GetEnvironmentVariable("STORAGE_SKIP_MOUNT"));

        if (this.SkipMount)
        {
            return;
        }

        this.SharePath = GetRequiredEnvironmentVariable("SHARE_PATH");
        this.User = GetRequiredEnvironmentVariable("AD_USER");
        this.Password = GetRequiredEnvironmentVariable("AD_PASSWORD");
        this.Domain = GetRequiredEnvironmentVariable("AD_DOMAIN");
        this.Vers = GetRequiredEnvironmentVariable("AD_VERS");
        this.Sec = GetRequiredEnvironmentVariable("SEC");
        this.Uid = GetRequiredEnvironmentVariable("UID");
        this.Gid = GetRequiredEnvironmentVariable("GID");
    }

    public bool IsMounted()
    {
        if (this.SkipMount)
        {
            return Directory.Exists(this.MountPath);
        }

        using var process = StartProcess("mountpoint", $"-q \"{this.MountPath}\"");
        process.WaitForExit();

        return process.ExitCode == 0;
    }

    public bool Mount()
    {
        if (this.SkipMount)
        {
            return Directory.Exists(this.MountPath);
        }

        Directory.CreateDirectory(this.MountPath);

        string options =
            $"username={this.User},password={this.Password},domain={this.Domain},vers={this.Vers},sec={this.Sec},uid={this.Uid},gid={this.Gid},noperm";

        using var process = StartProcess(
            "mount",
            $"-t cifs \"{this.SharePath}\" \"{this.MountPath}\" -o {options}");

        process.WaitForExit();
        return process.ExitCode == 0;
    }

    public static Process StartProcess(string filename, string arguments)
    {
        var psi = new ProcessStartInfo
        {
            FileName = filename,
            Arguments = arguments,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };

        var process = Process.Start(psi);

        if (process == null)
        {
            throw new InvalidOperationException($"Unable to start the process: {filename}");
        }

        return process;
    }

    private static string GetRequiredEnvironmentVariable(string name)
    {
        var value = Environment.GetEnvironmentVariable(name)?.Trim();

        if (string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException($"{name} is missing from the environment");
        }

        return value;
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
