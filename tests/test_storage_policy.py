from hpc_gui.services.storage_policy import StoragePolicyEvaluator


def test_no_metadata_and_outside_root_have_no_warning():
    assert StoragePolicyEvaluator({}).evaluate({"workdir": "/work/a"}) == ()
    provider = {"storage": [{"id": "scratch", "path_template": "/scratch", "policy": {"backup": False}}]}
    assert StoragePolicyEvaluator(provider).evaluate({"workdir": "/home/a"}) == ()


def test_backup_retention_and_cleanup_are_provider_driven():
    provider = {
        "storage": [{
            "id": "scratch",
            "path_template": "/scratch",
            "policy": {"backup": False, "retention_days": 14, "cleanup_note": "remove after download"},
        }]
    }
    warnings = StoragePolicyEvaluator(provider).evaluate({
        "workdir": "/scratch/job",
        "stdout": "/scratch/logs/job.out",
        "stderr": "/scratch/logs/job.err",
        "transfer": "/scratch/input.dat",
    })
    assert len(warnings) == 4
    assert warnings[0].messages == ("Not backed up", "Retention: 14 days", "Cleanup: remove after download")


def test_unresolved_and_unknown_policy_do_not_guess_capacity():
    provider = {"storage": [{"id": "work", "path_template": "/work", "policy": {}}]}
    assert StoragePolicyEvaluator(provider).evaluate({"workdir": None}) == ()
    assert StoragePolicyEvaluator(provider).evaluate({"workdir": "/work/job"}) == ()
