using System.Diagnostics;

namespace MailStorageService.Storage;

internal sealed class MountCheck : IMountCheck
{
    public bool IsMounted()
    {
        var Path = Environment.GetEnvironmentVariable("")
            ?? throw new InvalidOperationException("MOUNT_PATH is missing from the .env file");
        var process = Process.Start(new ProcessStartInfo
        {
            FileName = "mountpoint",
            ArgumentList = {"-q", Path},
            RedirectStandardOutput = true,
            RedirectStandardError = true
        } );

        process!.WaitForExit();
        
        return process.ExitCode==0;
    }

    public bool Mount()
    {
        return true;
    }
}