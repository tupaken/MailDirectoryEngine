using MailStorageService.Storage;

namespace MailStorageService.Tests;

internal sealed class FakeMountCheck : IMountCheck
{
    private readonly Queue<bool> mountedStates;

    public FakeMountCheck(params bool[] mountedStates)
    {
        if (mountedStates.Length == 0)
        {
            throw new ArgumentException("At least one mount state must be provided.", nameof(mountedStates));
        }

        this.mountedStates = new Queue<bool>(mountedStates);
    }

    public int MountCallCount { get; private set; }

    public bool IsMounted()
    {
        if (this.mountedStates.Count > 1)
        {
            return this.mountedStates.Dequeue();
        }

        return this.mountedStates.Peek();
    }

    public bool Mount()
    {
        this.MountCallCount++;
        return true;
    }
}

internal sealed class FakeStorageEngine : IStorageEngine
{
    private readonly bool result;

    public FakeStorageEngine(bool result)
    {
        this.result = result;
    }

    public bool Store(string sourcePath, string number)
    {
        return this.result;
    }
}

internal sealed class EnvironmentVariableScope : IDisposable
{
    private readonly Dictionary<string, string?> originalValues = new(StringComparer.Ordinal);

    public EnvironmentVariableScope(IReadOnlyDictionary<string, string?> overrides)
    {
        foreach (var entry in overrides)
        {
            this.originalValues[entry.Key] = Environment.GetEnvironmentVariable(entry.Key);
            Environment.SetEnvironmentVariable(entry.Key, entry.Value);
        }
    }

    public void Dispose()
    {
        foreach (var entry in this.originalValues)
        {
            Environment.SetEnvironmentVariable(entry.Key, entry.Value);
        }
    }
}
