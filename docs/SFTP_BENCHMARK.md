# SFTP Listing Performance

`scripts/benchmark_sftp_listing.py` measures the directory-streaming contract
without a GUI or a real cluster. It starts the disposable SSH/SFTP fixture used
by the wire tests and records connection/channel establishment separately from:

- time to first yielded entry,
- total enumeration time,
- repeated listings on the reused listing channel,
- parent -> child -> parent navigation.

The default sizes are approximately 100, 1,000, and 10,000 entries. Results are
machine-readable JSON and include a short console summary. Timings are synthetic
local measurements and must not be presented as HPC or FileZilla performance.

Run from the repository root:

```bash
PYTHONPATH=src python scripts/benchmark_sftp_listing.py --repeats 5 --json benchmarks/sftp_directory_listing_baseline.json
```

The committed baseline is a comparison point for future changes, not a CI timing
threshold. Repeat it on the same machine when comparing revisions and report the
median shown by the script. The benchmark does not change production behavior.

## GUI Listing Benchmark

`scripts/benchmark_remote_directory_gui.py` measures the Qt side separately:
it feeds fabricated progressive listings (100 / 1,000 / 10,000 entries) to the
real `RemoteDirPanel` in offscreen mode and records time to the first batch,
time to the first visible row, and total render time. It excludes SSH, SFTP,
and any real network entirely.

```bash
python scripts/benchmark_remote_directory_gui.py --repeats 5 --json benchmarks/remote_directory_gui_baseline.json
```

Use it together with the wire benchmark: the wire numbers explain remote
listing cost, the GUI numbers explain rendering/sort cost on top of it.
Neither number may be presented as HPC or FileZilla performance.

## Manual HPC/FileZilla Procedure

For an external comparison, use the same host, account, network/VPN state, remote
directory, and server-load conditions. Record RTT, packet loss, VPN status, and
known server load. Test cold and warm navigation for 100, 1,000, and 10,000-entry
directories where available. Record separately:

1. HPC Client GUI time to first visible entry.
2. HPC Client GUI full-listing time.
3. FileZilla observed navigation time.
4. FileZilla observed full-listing time.

FileZilla is a manual comparison tool only and is not a build or test dependency.
No real-HPC or FileZilla measurement was available for this local wave; external
validation remains manual.
