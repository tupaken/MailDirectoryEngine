namespace MailStorageService.Storage;

public interface IMountCheck
{
    bool IsMounted(string path);
}
