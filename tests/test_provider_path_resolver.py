from hpc_gui.services.provider_path_resolver import ProviderPathResolver


class FakeSSH:
    def __init__(self, output="/scratch/alice\n", code=0):
        self.output, self.code, self.calls = output, code, []

    def run(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return self.code, self.output, ""


def test_remote_resolver_allowlists_and_caches_fixed_lookup():
    ssh = FakeSSH()
    resolver = ProviderPathResolver(ssh)
    assert resolver.resolve("SCRATCH").path == "/scratch/alice"
    assert resolver.resolve("SCRATCH").state == "resolved"
    assert len(ssh.calls) == 1
    assert resolver.resolve("SECRET").state == "invalid"
    assert len(ssh.calls) == 1


def test_remote_resolver_rejects_bad_output_and_invalidates_cache():
    ssh = FakeSSH("relative\n")
    resolver = ProviderPathResolver(ssh)
    assert resolver.resolve("HOME").state == "invalid"
    ssh.output = "/home/alice\n"
    resolver.invalidate()
    assert resolver.resolve("HOME").path == "/home/alice"
    assert len(ssh.calls) == 2
