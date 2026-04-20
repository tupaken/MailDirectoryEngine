

using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Microsoft.AspNetCore.Routing.Constraints;

namespace MailStorageService.Storage;

internal sealed class StorageEngine
{
    private readonly MountCheck Check;
    private readonly string MountPath;
    private readonly string Directory2;
    private readonly string Directory3;
    public StorageEngine()
    {
        this.Check= new MountCheck();
        this.MountPath= Environment.GetEnvironmentVariable("MOUNT_PATH")
            ?? throw new InvalidOperationException ("MOUNT_PATH is missing from the .env file");
        this.Directory2=Environment.GetEnvironmentVariable("DIRECTORY2")
            ?? throw new InvalidOperationException ("DIRECTORY2 is missing from the .env file");
        this.Directory3=Environment.GetEnvironmentVariable("DIRECTORY3")
            ?? throw new InvalidOperationException("DIRECTORY3 is missing from .env file");
    }
    public bool Store(string SourcePath,string Number)
    {
        var isMounted = this.Check.IsMounted();

        if (!isMounted)
        {
            const int maxMountRetries = 5;

            for (int i = 0; i < maxMountRetries && !isMounted; i++)
            {
                this.Check.Mount();
                isMounted = this.Check.IsMounted();

                if (isMounted)
                    i=maxMountRetries+1;
                Thread.Sleep(1000);
            }

            if (!isMounted)
                return false;
        }

        var DestinationPath= FindPath(Number);
        
        if (DestinationPath==null)
            return false;

        if (CopyWithRsync(SourcePath,DestinationPath)==0)
            return true;
        
        return CopyWithRetry(SourcePath,DestinationPath);
    }

    private int CopyWithRsync(string SourcePath,string DestinationPath)
    {   
        string FileName="rsync";
        string Arguments=$"-av --partial --inplace \"{SourcePath}\" \"{DestinationPath}\"";
        using var process = MountCheck.StartProcess(FileName,Arguments);

        process.WaitForExit();

        return process.ExitCode;
    }

    private bool CopyWithRetry(string SourcePath,string DestinationPath)
    {
        int maxRetries = 5;

        for (int i = 1; i <= maxRetries; i++)
        {
            Console.WriteLine($"Try {i}");

            if (CopyWithRsync(SourcePath,DestinationPath)==0)
                {
                    Console.WriteLine("✅ Copying successful");
                    return true;
                }
            
            Console.WriteLine("❌ Error – please wait and try again...");
            Thread.Sleep(5000);
        }       
        Console.WriteLine("🚨 Failed completely");
        return false;
    }

    private string? FindPath(string number)
    {
        var level1 = Directory.EnumerateDirectories(this.MountPath, number + "*");

        foreach (var d1 in level1)
        {
            var d2 = Directory.EnumerateDirectories(d1, $"*{this.Directory2}*", SearchOption.AllDirectories)
                .FirstOrDefault();

            if (d2 == null) continue;

            var d3 = Directory.EnumerateDirectories(d2, "*", SearchOption.AllDirectories)
                .FirstOrDefault(x => Normalize(Path.GetFileName(x)).Contains(Normalize(this.Directory3)));

            if (d3 != null)
                return d3; 
        }

        return null;
    }

    static string Normalize(string input)
    {
        return new string(
            input
                .ToLowerInvariant()
                .Where(char.IsLetterOrDigit)
                .ToArray());
    }
}
