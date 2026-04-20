using System;
using System.Diagnostics;

namespace MailStorageService.Storage;

internal sealed class MountCheck : IMountCheck
{
    private readonly string MountPath;
    private readonly string SharePath;
    private readonly string User;
    private readonly string Password;
    private readonly string Domain;
    private readonly string Vers;
    private readonly string Sec;
    private readonly string Uid;
    private readonly string Gid;

    public MountCheck()
    {
        this.MountPath=Environment.GetEnvironmentVariable("MOUNT_PATH")
            ?? throw new InvalidOperationException("MOUNT_PATH is missing from the .env file");
        this.SharePath=Environment.GetEnvironmentVariable("SHARE_PATH")
            ?? throw new InvalidOperationException("SHARE_PATH is missing from the .env file");
        this.User=Environment.GetEnvironmentVariable("AD_USER")
            ?? throw new InvalidOperationException("AD_USER is missing from the .env file");
        this.Password=Environment.GetEnvironmentVariable("AD_PASSWORD")
            ?? throw new InvalidOperationException("AD_PASSWORD is missing from the .env file");
        this.Domain=Environment.GetEnvironmentVariable("AD_DOMAIN")
            ?? throw new InvalidOperationException("AD_DOMAIN is missing from the .env file");
        this.Vers=Environment.GetEnvironmentVariable("AD_VERS")
            ?? throw new InvalidOperationException("AD_VERS is missing from the .env file");
        this.Sec=Environment.GetEnvironmentVariable("SEC")
            ?? throw new InvalidOperationException("SEC is missing from the .env file");
        this.Uid=Environment.GetEnvironmentVariable("UID")
            ?? throw new InvalidOperationException("UID is missing from the .env file");
        this.Gid=Environment.GetEnvironmentVariable("GID")
            ?? throw new InvalidOperationException("GID is missing from the .env file");
    
    }
    public bool IsMounted()
    {
        var process = StartProcess("mountpoint",$"-q {this.MountPath}");
        
        process!.WaitForExit();
        
        return process.ExitCode==0;
    }

    public bool Mount()
    {
        string optinons =$"username={this.User},password={this.Password},domain={this.Domain},vers={this.Vers},sec={this.Sec},uid={this.Uid},gid={this.Gid},noperm";

        using var process = StartProcess("sudo",
            $"mount -t cifs {this.SharePath} {this.MountPath} -o {optinons}");
        
        process.WaitForExit();
        return process.ExitCode == 0;
    }

    public static Process StartProcess(string filename,string arguments)
    {
        var psi = new ProcessStartInfo
        {
            FileName=filename,
            Arguments=arguments,
            RedirectStandardOutput=true,
            RedirectStandardError=true
        };

        var process = Process.Start(psi);
        
        if (process == null)
            throw new InvalidOperationException($"Unable to start the process: {filename}");

        return process;
    }

}