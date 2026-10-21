from hpc_gui.services.job_paths import resolve_job_directory


def test_verified_workdir_precedes_all_fallbacks():
    resolved = resolve_job_directory({
        "workdir": "/verified/work", "last_workdir": "/cached/work",
        "stdout_path": "/output/slurm-4.out",
    })
    assert (resolved.path, resolved.source, resolved.verified) == (
        "/verified/work", "slurm_workdir", True,
    )


def test_cached_and_submit_directories_are_marked_as_fallbacks():
    cached = resolve_job_directory({"last_workdir": "/cached/work"})
    submit = resolve_job_directory({"submit_directory": "/submit"})
    assert cached.path == "/cached/work" and not cached.verified
    assert submit.path == "/submit" and not submit.verified


def test_output_parent_is_last_resort_and_empty_never_becomes_root():
    output = resolve_job_directory({"stdout_path": "/work/logs/job.out"})
    missing = resolve_job_directory({})
    assert output.path == "/work/logs"
    assert output.source == "output_parent"
    assert missing.path == ""
