import json
import zipfile

from hpc_gui.services.reproducibility_bundle import export_job_bundle


def test_offline_export_contains_versioned_job_script_and_readme(tmp_path):
    path = export_job_bundle({"job_id": "123", "script_text": "#!/bin/bash\necho ok", "provider_id": "truba"}, tmp_path)
    with zipfile.ZipFile(path) as bundle:
        names = set(bundle.namelist())
        job = json.loads(bundle.read("job.json"))
        assert {"job.json", "submitted_script.sh", "README.txt"} <= names
        assert job["bundle_schema"] == "hpc-reproducibility/1"


def test_environment_is_off_by_default_and_redacted_when_explicit(tmp_path):
    record = {"job_id": "1", "script_text": "run", "password": "bad"}
    default = export_job_bundle(record, tmp_path / "default")
    with zipfile.ZipFile(default) as bundle:
        assert "environment.json" not in bundle.namelist()
        assert "password" not in bundle.read("job.json").decode().lower()
    explicit = export_job_bundle(record, tmp_path / "explicit", environment={"SAFE": "yes", "TOKEN": "bad"}, include_environment=True)
    with zipfile.ZipFile(explicit) as bundle:
        env = bundle.read("environment.json").decode()
        assert "SAFE" in env and "TOKEN" not in env


def test_missing_script_is_exported_without_failure(tmp_path):
    path = export_job_bundle({"job_id": "2"}, tmp_path)
    with zipfile.ZipFile(path) as bundle:
        assert "submitted_script.sh" not in bundle.namelist()
