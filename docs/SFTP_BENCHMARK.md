# SFTP Listing Performance

`scripts/benchmark_sftp_listing.py` starts the disposable Paramiko SSH/SFTP
fixture and measures channel establishment separately from first-entry latency,
full enumeration, repeated listings on the reused listing channel, and
parent → child → parent navigation for approximately 100, 1,000, and 10,000
entries.

Run from the repository root:

```bash
PYTHONPATH=src python scripts/benchmark_sftp_listing.py --repeats 5 \
  --json benchmarks/sftp_directory_listing_baseline.json
```

The committed JSON is a synthetic/local baseline. It excludes GUI rendering and
real network conditions, is not a CI timing threshold, and must not be presented
as HPC or FileZilla performance. Compare medians on the same machine.

## Manual HPC/FileZilla procedure

Use the same host, account, VPN/network state, remote directory, and known server
load. Record RTT, packet loss, and VPN status. Test cold and warm navigation for
100 / 1,000 / 10,000-entry directories where available, recording separately:

1. HPC Client GUI first visible entry and full-listing time.
2. FileZilla observed first visible entry and full-listing time.

FileZilla remains a manual comparison tool and is not a build or test dependency.
No real-HPC or FileZilla measurement was available for this wave.
