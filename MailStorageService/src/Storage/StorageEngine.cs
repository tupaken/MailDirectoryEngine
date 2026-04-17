

using Microsoft.AspNetCore.Routing.Constraints;

namespace MailStorageService.Storage;

internal sealed class StorageEngine
{
    private readonly MountCheck Check;
    public StorageEngine()
    {
        this.Check= new MountCheck();
    }
    public bool Store(string SourcePath,int Number)
    {
        if (!this.Check.IsMounted())
        {
            //TODO: remount and check
        }
        if (CopyWithRsync(SourcePath,DestinationPath)==0)
            return true;
        
        return CopyWithRsync(SourcePath,DestinationPath);
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
}