namespace MailStorageService.Storage;

internal interface IMountCheck
{
    bool IsMounted();
    bool Mount(); 
}
