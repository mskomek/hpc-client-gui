# Live Slurm Draft Acceptance

Date: 2026-10-23

## Result

Status: PASS for read-only discovery and scheduler test-only validation; BLOCKED for the requested Tailscale-to-HPC route and full GUI transfer workflow.

The real lab scheduler reported Slurm 23.11.4. An isolated one-node, one-CPU, one-minute draft used partition debug and account local. The generated draft and journal hashes are recorded in evidence/live-slurm-testonly-final.json.

sbatch --test-only returned exit code 0 with “Job 346 to start … on nodes compute01 in partition debug.” The queue was empty both before and after. No job ID was submitted or returned, cleanup passed, and the result is PASS_TEST_ONLY_NO_SUBMISSION. No sbatch submission, srun, salloc, or Fluent solver job was started.

The draft contained a single node/task, cpus-per-task, a one-minute walltime, isolated work paths, Fluent 25.2 configuration, solver/MPI selections, output/error paths, and journal hash. Scheduler acceptance verifies the script's syntax and scheduler profile only; it does not prove a Fluent executable/module exists or that a solve will run.

The exact current-source GUI Jobs-editor handoff and user-visible no-auto-submit interaction were not performed. The live test used the existing development-host lab path, not a Tailscale route from the remote workstation.

Evidence: evidence/live-slurm-testonly-final.json in the handoff ZIP.
