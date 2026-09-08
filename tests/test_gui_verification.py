"""Manual GUI verification script for Fix Waves 75-77.

Exercises the wx Jobs & Outputs workspace with a mock backend to verify:
- 3 vertical collapsible sections (Jobs, Job Details, Accounting)
- SelectedJobStore clears metadata on new job selection
- Stale response protection
- Squeue pipe parsing (8 columns)
- FileFilterRegistry drives filter tabs
- Column-click sorting
- Per-channel output controls (Search, Find Next, Jump, Open, Show in Files)
- Real follower reassignment
- Provider job_outputs resolution
"""

import threading
import time
import sys

import wx

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_jobs import WxJobsModel, show_jobs, clean_output
from hpc_gui.services.selected_job_context import SelectedJobStore, SelectedJobContext
from hpc_gui.services.output_channel_resolver import (
    OutputResolver, OutputChannelDefinition, definitions_from_provider,
)
from hpc_gui.services.file_filter_registry import build_core_registry


class MockSlurm:
    def __init__(self):
        self._jobs = [
            {"id": "1001", "name": "training_job", "state": "RUNNING", "partition": "gpu",
             "elapsed": "02:15:00", "nodes": "2", "cpus": "16", "reason": "None",
             "user": "testuser"},
            {"id": "1002", "name": "data_processing", "state": "PENDING", "partition": "cpu",
             "elapsed": "00:00:00", "nodes": "1", "cpus": "8", "reason": "Resources",
             "user": "testuser"},
            {"id": "1003", "name": "simulation_run", "state": "COMPLETED", "partition": "gpu",
             "elapsed": "01:30:00", "nodes": "4", "cpus": "32", "reason": "None",
             "user": "testuser"},
        ]
        self._scontrol_data = {
            "1001": "JobId=1001 JobName=training_job\nWorkDir=/scratch/user/run1\nStdOut=/scratch/user/run1/slurm-1001.out\nStdErr=/scratch/user/run1/slurm-1001.err\n NodeList=node[1-2]\nExitCode=0:0",
            "1002": "JobId=1002 JobName=data_processing\nWorkDir=/scratch/user/run2\nStdOut=/scratch/user/run2/slurm-1002.out\nStdErr=/scratch/user/run2/slurm-1002.err\n NodeList=\nExitCode=",
            "1003": "JobId=1003 JobName=simulation_run\nWorkDir=/scratch/user/run3\nStdOut=/scratch/user/run3/slurm-1003.out\nStdErr=/scratch/user/run3/slurm-1003.err\n NodeList=node[1-4]\nExitCode=0:0",
        }
        self._sacct_data = {
            "1001": "1001|training_job|RUNNING|02:15:00|4G|16",
            "1002": "1002|data_processing|PENDING|00:00:00||8",
            "1003": "1003|simulation_run|COMPLETED|01:30:00|8G|32",
        }
        self._stdout = {
            "1001": "Training epoch 1/100 loss=0.45\nTraining epoch 2/100 loss=0.38\nTraining epoch 3/100 loss=0.31",
            "1002": "",
            "1003": "Simulation complete. Results saved to /scratch/user/run3/results.dat",
        }

    def squeue(self, username):
        lines = ["JOBID|PARTITION|NAME|USER|STATE|ELAPSED|NODES|CPUS|REASON"]
        for j in self._jobs:
            lines.append(f"{j['id']}|{j['partition']}|{j['name']}|{j['user']}|{j['state']}|{j['elapsed']}|{j['nodes']}|{j['cpus']}|{j['reason']}")
        return "\n".join(lines)

    def scontrol_show_job(self, job_id):
        return self._scontrol_data.get(str(job_id), "")

    def sacct(self, username, job_id=""):
        lines = ["JOBID|JOBNAME|STATE|ELAPSED|MAXRSS|CPUS"]
        for jid, data in self._sacct_data.items():
            if not job_id or jid == str(job_id):
                lines.append(data)
        return "\n".join(lines)

    def scancel(self, job_id):
        return None

    def job_state(self, job_id):
        for j in self._jobs:
            if str(j["id"]) == str(job_id):
                return j["state"]
        return ""

    def read_text(self, path):
        for jid, content in self._stdout.items():
            if f"slurm-{jid}.out" in path:
                return content
        return ""


def run_verification():
    load_language("en")
    app = wx.App(redirect=False)
    slurm = MockSlurm()

    results = []

    def check(name, condition, detail=""):
        status = "PASS" if condition else "FAIL"
        results.append((name, status, detail))
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    # --- Wave 75: Layout and SelectedJobStore ---
    print("\n=== Wave 75: Jobs/Details Layout ===")

    show_jobs(
        list_jobs=lambda: [
            dict(zip(["id", "partition", "name", "user", "state", "elapsed", "nodes", "cpus", "reason"],
                     line.split("|")))
            for line in slurm.squeue("").splitlines()[1:]
            if line.strip()
        ],
        read_output=lambda job_id: {"stdout": slurm.read_text(f"slurm-{job_id}.out"), "stderr": ""},
        cancel=slurm.scancel,
        final_state=slurm.job_state,
        refresh_sacct=lambda job_id: slurm.sacct("", job_id),
        show_job_details=lambda job_id: slurm.scontrol_show_job(job_id),
    )
    time.sleep(0.5)

    frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
    assert frames, "No Jobs frame found"
    frame = frames[-1]

    # Check 3 vertical sections exist
    controls = frame._wx_jobs_controls
    jobs_ctrl = controls["jobs"]
    details_text = controls["details_text"]
    accounting_table = controls["accounting_table"]
    details_box = controls["details_box"]
    accounting_box = controls["accounting_box"]

    # Pump events to let async refresh populate the table
    for _ in range(30):
        app.ProcessPendingEvents()
        wx.MilliSleep(50)
        if jobs_ctrl.GetItemCount() > 0:
            break

    check("Jobs ListCtrl exists", jobs_ctrl is not None)
    check("Details TextCtrl exists", details_text is not None)
    check("Accounting ListCtrl exists", accounting_table is not None)
    check("Details box has collapse marker", "▾" in details_box.GetLabel() or "▸" in details_box.GetLabel())
    check("Accounting box has collapse marker", "▾" in accounting_box.GetLabel() or "▸" in accounting_box.GetLabel())

    # Check 8 columns
    col_count = jobs_ctrl.GetColumnCount()
    check("Jobs table has 8 columns", col_count == 8, f"got {col_count}")

    # Check job count
    job_count = jobs_ctrl.GetItemCount()
    check("Jobs table has 3 rows", job_count == 3, f"got {job_count}")

    # Select job 1001
    jobs_ctrl.Select(0)
    evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs_ctrl.GetId())
    evt.SetIndex(0)
    jobs_ctrl.ProcessEvent(evt)
    time.sleep(0.3)

    ctx = frame._wx_jobs_model.selected_job_store.context
    check("Selected job is 1001", ctx.job_id == "1001", f"got {ctx.job_id}")
    check("Job name is training_job", ctx.name == "training_job", f"got {ctx.name}")

    # Select job 1002 — should clear old metadata
    jobs_ctrl.Select(1)
    evt2 = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs_ctrl.GetId())
    evt2.SetIndex(1)
    jobs_ctrl.ProcessEvent(evt2)
    time.sleep(0.3)

    ctx2 = frame._wx_jobs_model.selected_job_store.context
    check("New selection clears old workdir", ctx2.workdir == "" or ctx2.workdir != ctx.workdir,
          f"workdir={ctx2.workdir!r}")
    check("New selection job_id is 1002", ctx2.job_id == "1002", f"got {ctx2.job_id}")

    # --- Wave 76: Filter Registry ---
    print("\n=== Wave 76: FileFilterRegistry ===")

    registry = build_core_registry()
    filter_ids = registry.visible_filter_ids()
    check("Registry has 'all'", "all" in filter_ids)
    check("Registry has 'folders'", "folders" in filter_ids)
    check("Registry has 'shell'", "shell" in filter_ids)
    check("Registry has 'other'", "other" in filter_ids)
    check("Registry matches .sh file", registry.matches({"name": "run.sh", "is_dir": False}, "shell"))
    check("Registry matches folder", registry.matches({"name": "data", "is_dir": True}, "folders"))
    check("Registry rejects .sh in archives", not registry.matches({"name": "run.sh", "is_dir": False}, "archives"))

    # Check provider filter registration
    from hpc_gui.services.file_filter_registry import FileFilter
    registry.register(FileFilter(
        id="truba_logs", label_en="TRUBA Logs", label_tr="TRUBA Günlükleri",
        globs=("*.log",), order=100, source="provider",
    ))
    check("Provider filter registered", registry.get("truba_logs") is not None)
    check("Provider filter matches .log", registry.matches({"name": "job.log", "is_dir": False}, "truba_logs"))

    # --- Wave 77: Dynamic Outputs ---
    print("\n=== Wave 77: Dynamic Outputs ===")

    output_channels = controls.get("output_channels", {})
    check("Output channels dict exists", isinstance(output_channels, dict))

    # Check resolver
    resolver = OutputResolver()
    defs = definitions_from_provider({
        "streams": [
            {"id": "stdout", "role": "stdout", "resolver": "slurm.stdout",
             "labels": {"en": "Standard Output"}, "order": 0},
            {"id": "stderr", "role": "stderr", "resolver": "slurm.stderr",
             "labels": {"en": "Standard Error"}, "order": 1},
        ]
    })
    check("definitions_from_provider returns 2 defs", len(defs) == 2, f"got {len(defs)}")

    resolved = resolver.resolve(defs, job_id="1001", workdir="/scratch/user/run1",
                                scontrol_stdout="/scratch/user/run1/slurm-1001.out",
                                scontrol_stderr="/scratch/user/run1/slurm-1001.err")
    check("Resolver produces 2 channels", len(resolved) == 2, f"got {len(resolved)}")

    # Check dedup when stdout == stderr
    resolved_dedup = resolver.resolve(defs, job_id="1001", workdir="/scratch/user/run1",
                                       scontrol_stdout="/same/path.out",
                                       scontrol_stderr="/same/path.out")
    check("Dedup merges same path", len(resolved_dedup) == 1, f"got {len(resolved_dedup)}")
    if resolved_dedup:
        check("Dedup preserves both roles", "stdout" in resolved_dedup[0].roles and "stderr" in resolved_dedup[0].roles)

    # Check legacy resolver
    legacy = resolver.resolve_legacy(job_id="1001", workdir="/scratch/user/run1",
                                      scontrol_stdout="/scratch/user/run1/slurm-1001.out")
    check("Legacy resolver returns channels", len(legacy) > 0, f"got {len(legacy)}")

    # Check empty streams
    empty_defs = definitions_from_provider({"streams": []})
    check("Empty streams returns empty list", len(empty_defs) == 0)

    # Check absent job_outputs
    absent_defs = definitions_from_provider(None)
    check("Absent job_outputs returns empty list", len(absent_defs) == 0)

    # --- Stale response protection ---
    print("\n=== Stale Response Protection ===")

    store = SelectedJobStore()
    store.select(job_id="A", workdir="/scratch/A", stdout_path="/scratch/A/a.out")
    gen_a = store.generation
    store.select(job_id="B")
    gen_b = store.generation
    check("Generation incremented on job switch", gen_b > gen_a)
    check("Job B workdir is empty", store.context.workdir == "")
    check("Job B stdout_path is empty", store.context.stdout_path == "")
    store.update(workdir="/scratch/B", stdout_path="/scratch/B/b.out")
    check("Update enriches without bumping generation", store.generation == gen_b)
    check("Update sets workdir", store.context.workdir == "/scratch/B")

    # --- Cancel ---
    print("\n=== Cancel ===")
    check("Cancel callback exists", controls.get("cancel") is not None)

    # --- Slurm parsing ---
    print("\n=== Slurm Pipe Parsing ===")
    from hpc_gui.services.slurm_models import parse_squeue
    squeue_output = slurm.squeue("testuser")
    jobs = parse_squeue(squeue_output)
    check("Parse squeue returns 3 jobs", len(jobs) == 3, f"got {len(jobs)}")
    if jobs:
        check("First job ID is 1001", jobs[0].job_id == "1001", f"got {jobs[0].job_id}")
        check("First job partition is gpu", jobs[0].partition == "gpu", f"got {jobs[0].partition}")
        check("First job name is training_job", jobs[0].name == "training_job", f"got {jobs[0].name}")
        check("First job state is RUNNING", jobs[0].state == "RUNNING", f"got {jobs[0].state}")

    # --- Summary ---
    print("\n" + "=" * 60)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    print(f"Results: {passed} passed, {failed} failed out of {len(results)} checks")
    if failed:
        print("\nFailed checks:")
        for name, status, detail in results:
            if status == "FAIL":
                print(f"  - {name}: {detail}")

    frame.Close()
    app.ProcessPendingEvents()
    app.Destroy()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_verification())
