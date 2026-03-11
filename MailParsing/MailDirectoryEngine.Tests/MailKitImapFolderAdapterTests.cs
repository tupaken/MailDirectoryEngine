using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using MailDirectoryEngine.src.Imap;
using MailKit;
using MailKit.Search;
using MimeKit;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class MailKitImapFolderAdapterTests
{
    /// <summary>
    /// Verifies that constructing the folder adapter with a null folder throws.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenFolderIsNull()
    {
        var ex = Assert.Throws<ArgumentNullException>(() => new MailKitImapFolderAdapter(null!));
        Assert.Equal("folder", ex.ParamName);
    }

    /// <summary>
    /// Verifies that folder metadata properties proxy the underlying MailKit folder values.
    /// </summary>
    [Fact]
    public void Name_FullName_AndCount_ProxyUnderlyingFolderValues()
    {
        var (folder, _) = CreateMailFolderProxy(
            name: "Inbox",
            fullName: "Root/Inbox",
            count: 42);

        var adapter = new MailKitImapFolderAdapter(folder);

        Assert.Equal("Inbox", adapter.Name);
        Assert.Equal("Root/Inbox", adapter.FullName);
        Assert.Equal(42, adapter.Count);
    }

    /// <summary>
    /// Verifies that open requests are forwarded to the underlying folder.
    /// </summary>
    [Fact]
    public void Open_DelegatesAccessMode()
    {
        var (folder, proxy) = CreateMailFolderProxy(
            name: "Inbox",
            fullName: "Root/Inbox",
            count: 1);

        var adapter = new MailKitImapFolderAdapter(folder);

        adapter.Open(FolderAccess.ReadOnly);

        Assert.Equal(FolderAccess.ReadOnly, proxy.LastOpenAccess);
    }

    /// <summary>
    /// Verifies that subfolders are returned as adapted <see cref="IImapFolder"/> instances.
    /// </summary>
    [Fact]
    public void GetSubfolders_ReturnsAdaptedSubfolders()
    {
        var (child1, _) = CreateMailFolderProxy("Archive", "Root/Archive", 3);
        var (child2, _) = CreateMailFolderProxy("Sent", "Root/Sent", 5);
        var (folder, proxy) = CreateMailFolderProxy("Root", "Root", 0);
        proxy.Subfolders.Add(child1);
        proxy.Subfolders.Add(child2);

        var adapter = new MailKitImapFolderAdapter(folder);

        var result = adapter.GetSubfolders(recursive: true).ToList();

        Assert.Equal(2, result.Count);
        Assert.All(result, item => Assert.IsType<MailKitImapFolderAdapter>(item));
        Assert.Equal(new[] { "Archive", "Sent" }, result.Select(r => r.Name).ToArray());
    }

    /// <summary>
    /// Verifies that search results are forwarded unchanged from the underlying folder.
    /// </summary>
    [Fact]
    public void Search_ReturnsConfiguredUids()
    {
        var uid1 = new UniqueId(10);
        var uid2 = new UniqueId(20);
        var (folder, proxy) = CreateMailFolderProxy("Inbox", "Root/Inbox", 2);
        proxy.SearchResults = new List<UniqueId> { uid1, uid2 };

        var adapter = new MailKitImapFolderAdapter(folder);

        var result = adapter.Search(SearchQuery.All);

        Assert.Equal(new[] { uid1, uid2 }, result);
    }

    /// <summary>
    /// Verifies that message retrieval returns the configured underlying MIME message.
    /// </summary>
    [Fact]
    public void GetMessage_ReturnsConfiguredMessage()
    {
        var uid = new UniqueId(77);
        var message = new MimeMessage();
        message.Subject = "Proxy Subject";

        var (folder, proxy) = CreateMailFolderProxy("Inbox", "Root/Inbox", 1);
        proxy.Messages[uid] = message;

        var adapter = new MailKitImapFolderAdapter(folder);

        var result = adapter.GetMessage(uid);

        Assert.Same(message, result);
        Assert.Equal("Proxy Subject", result.Subject);
    }

    /// <summary>
    /// Creates a dispatch proxy and strongly typed helper used to emulate an <see cref="IMailFolder"/>.
    /// </summary>
    /// <param name="name">Folder display name.</param>
    /// <param name="fullName">Folder full path.</param>
    /// <param name="count">Reported message count.</param>
    /// <returns>The proxied MailKit folder and its backing test proxy.</returns>
    private static (IMailFolder folder, TestMailFolderProxy proxy) CreateMailFolderProxy(
        string name,
        string fullName,
        int count)
    {
        var folder = DispatchProxy.Create<IMailFolder, TestMailFolderProxy>();
        var proxy = (TestMailFolderProxy)(object)folder;
        proxy.NameValue = name;
        proxy.FullNameValue = fullName;
        proxy.CountValue = count;
        return (folder, proxy);
    }
}

internal class TestMailFolderProxy : DispatchProxy
{
    public string NameValue { get; set; } = string.Empty;
    public string FullNameValue { get; set; } = string.Empty;
    public int CountValue { get; set; }
    public FolderAccess? LastOpenAccess { get; private set; }
    public IList<UniqueId> SearchResults { get; set; } = new List<UniqueId>();
    public Dictionary<UniqueId, MimeMessage> Messages { get; } = new();
    public IList<IMailFolder> Subfolders { get; } = new List<IMailFolder>();

    /// <summary>
    /// Handles proxy member invocations for the test double.
    /// </summary>
    /// <param name="targetMethod">Method requested through the proxy.</param>
    /// <param name="args">Arguments supplied to the proxied call.</param>
    /// <returns>Configured return value matching the invoked member.</returns>
    protected override object? Invoke(MethodInfo? targetMethod, object?[]? args)
    {
        if (targetMethod is null)
            throw new InvalidOperationException("Expected target method for proxy invocation.");

        switch (targetMethod.Name)
        {
            case "get_Name":
                return NameValue;
            case "get_FullName":
                return FullNameValue;
            case "get_Count":
                return CountValue;
            case "Open":
                if (args != null)
                {
                    foreach (var arg in args)
                    {
                        if (arg is FolderAccess access)
                        {
                            LastOpenAccess = access;
                            break;
                        }
                    }
                }
                if (targetMethod.ReturnType == typeof(void))
                    return null;
                if (targetMethod.ReturnType.IsValueType)
                    return Activator.CreateInstance(targetMethod.ReturnType);
                return null;
            case "GetSubfolders":
                return Subfolders;
            case "Search":
                return SearchResults;
            case "GetMessage":
                var uid = (UniqueId)args![0]!;
                return Messages[uid];
            case "Dispose":
                return null;
            default:
                if (targetMethod.ReturnType == typeof(void))
                    return null;
                if (targetMethod.ReturnType.IsValueType)
                    return Activator.CreateInstance(targetMethod.ReturnType);
                return null;
        }
    }
}
