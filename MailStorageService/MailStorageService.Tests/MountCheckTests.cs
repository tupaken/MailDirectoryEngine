using MailStorageService.Storage;

namespace MailStorageService.Tests;

public class MountCheckTests
{
    /// <summary>
    /// Verifies that skip-mount mode only requires the mount path.
    /// </summary>
    [Fact]
    public void Constructor_DoesNotRequireShareSettings_WhenSkipMountEnabled()
    {
        using var scope = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            ["MOUNT_PATH"] = " /mounted-share ",
            ["STORAGE_SKIP_MOUNT"] = "true",
            ["SHARE_PATH"] = null,
            ["AD_USER"] = null,
            ["AD_PASSWORD"] = null,
            ["AD_DOMAIN"] = null,
            ["AD_VERS"] = null,
            ["SEC"] = null,
            ["UID"] = null,
            ["GID"] = null
        });

        var exception = Record.Exception(() => new MountCheck());

        Assert.Null(exception);
    }

    /// <summary>
    /// Verifies that required SMB settings are validated when skip-mount is disabled.
    /// </summary>
    [Fact]
    public void Constructor_Throws_WhenSharePathIsMissing()
    {
        using var scope = new EnvironmentVariableScope(new Dictionary<string, string?>
        {
            ["MOUNT_PATH"] = "/mounted-share",
            ["STORAGE_SKIP_MOUNT"] = "false",
            ["SHARE_PATH"] = null,
            ["AD_USER"] = "user",
            ["AD_PASSWORD"] = "password",
            ["AD_DOMAIN"] = "domain",
            ["AD_VERS"] = "3.0",
            ["SEC"] = "ntlmssp",
            ["UID"] = "0",
            ["GID"] = "0"
        });

        var exception = Assert.Throws<InvalidOperationException>(() => new MountCheck());

        Assert.Equal("SHARE_PATH is missing from the environment", exception.Message);
    }

    /// <summary>
    /// Verifies that skip-mount mode delegates the mounted state to the local directory check.
    /// </summary>
    [Fact]
    public void IsMounted_ReturnsDirectoryState_WhenSkipMountEnabled()
    {
        var check = new MountCheck(
            mountPath: "/mounted-share",
            skipMount: true,
            runProcess: static (_, _) => throw new InvalidOperationException("Process runner should not be used."),
            directoryExists: path => path == "/mounted-share");

        var result = check.IsMounted();

        Assert.True(result);
    }

    /// <summary>
    /// Verifies that the mountpoint command determines the mounted state when self-mounting is enabled.
    /// </summary>
    [Fact]
    public void IsMounted_ReturnsTrue_WhenMountpointCommandSucceeds()
    {
        string? fileName = null;
        string? arguments = null;

        var check = new MountCheck(
            mountPath: "/mounted-share",
            skipMount: false,
            runProcess: (currentFileName, currentArguments) =>
            {
                fileName = currentFileName;
                arguments = currentArguments;
                return 0;
            },
            sharePath: "//server/share",
            user: "user",
            password: "password",
            domain: "domain",
            vers: "3.0",
            sec: "ntlmssp",
            uid: "0",
            gid: "0");

        var result = check.IsMounted();

        Assert.True(result);
        Assert.Equal("mountpoint", fileName);
        Assert.Equal("-q \"/mounted-share\"", arguments);
    }

    /// <summary>
    /// Verifies that mount operations create the local directory and execute the expected CIFS command.
    /// </summary>
    [Fact]
    public void Mount_UsesExpectedCifsCommand_WhenSkipMountDisabled()
    {
        string? createdDirectory = null;
        string? fileName = null;
        string? arguments = null;

        var check = new MountCheck(
            mountPath: "/mounted-share",
            skipMount: false,
            runProcess: (currentFileName, currentArguments) =>
            {
                fileName = currentFileName;
                arguments = currentArguments;
                return 0;
            },
            createDirectory: path => createdDirectory = path,
            sharePath: "//server/share",
            user: "user",
            password: "password",
            domain: "domain",
            vers: "3.0",
            sec: "ntlmssp",
            uid: "0",
            gid: "0");

        var result = check.Mount();

        Assert.True(result);
        Assert.Equal("/mounted-share", createdDirectory);
        Assert.Equal("mount", fileName);
        Assert.Equal(
            "-t cifs \"//server/share\" \"/mounted-share\" -o username=user,password=password,domain=domain,vers=3.0,sec=ntlmssp,uid=0,gid=0,noperm",
            arguments);
    }
}
