# Transfer Throughput Benchmark (manual HPC validation)

The committed `benchmarks/sftp_transfer_baseline.json` is a **synthetic local
measurement** against the in-repo disposable SSH/SFTP fixture. It exists to
detect code regressions and must never be presented as TRUBA, HPC, or
FileZilla performance.

## Manual real-HPC procedure

For a meaningful external measurement, hold everything constant except the
variable under test:

- same login/host pair;
- same account;
- same remote path (`/arf/home/<user>/...` or equivalent);
- same network and VPN state;
- same server-load window (avoid shared-node bursts);
- the exact same file set for both tools.

Run each configuration separately for **upload** and **download**:

1. single large file (for example 1 GiB);
2. many small files (for example 2,000 × 64 KiB);
3. repeat at application parallel limits **1**, **2**, and **4**
   (*Advanced → Maximum simultaneous transfers*);
4. repeat the best configuration in FileZilla as a manual comparison point.

Record wall-clock time, achieved MiB/s, and any throttling or channel errors.
Note RTT and packet loss during the window. FileZilla is a manual comparison
tool only — it is not a build or test dependency of this project, and no
fabricated results are committed to this repository.

Remember: concurrent settings apply to **multiple files**; a single large file
is transferred by one stream and is not segmented.
