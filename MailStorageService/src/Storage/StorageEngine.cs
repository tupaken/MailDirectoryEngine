

namespace MailStorageService.Storage;

internal sealed class StorageEngine
{
    private readonly MountCheck Check;
    public StorageEngine()
    {
        this.Check= new MountCheck();
    }
    public bool Strore()
    {
        this.Check.IsMounted();
        
        return true;
    }

}