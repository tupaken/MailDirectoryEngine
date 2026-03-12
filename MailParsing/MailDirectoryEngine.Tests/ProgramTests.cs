using MailDirectoryEngine.src;
using Xunit;

namespace MailDirectoryEngine.Tests;

public class ProgramTests
{
    /// <summary>
    /// Verifies that hashing uses the expected uppercase SHA-256 representation.
    /// </summary>
    [Fact]
    public void ComputeHash_ReturnsExpectedUppercaseSha256Digest()
    {
        var hash = Program.ComputeHash("abc");

        Assert.Equal(
            "BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD",
            hash);
    }

    /// <summary>
    /// Verifies that hashing an empty string still returns a valid deterministic digest.
    /// </summary>
    [Fact]
    public void ComputeHash_ReturnsExpectedDigest_ForEmptyString()
    {
        var hash = Program.ComputeHash(string.Empty);

        Assert.Equal(
            "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
            hash);
    }
}
