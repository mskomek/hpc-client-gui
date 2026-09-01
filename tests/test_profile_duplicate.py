from hpc_gui.services.profile_duplicate import duplicate_profile


def test_duplicate_is_independent_and_drops_credentials():
    original = {"id": "one", "name": "Cluster", "host": "h", "password_dpapi": "x", "provider": {"safe": True, "token": "y"}}
    duplicate = duplicate_profile(original, ["Cluster"])
    assert duplicate["id"] != original["id"]
    assert duplicate["name"] == "Cluster (copy)"
    assert "password_dpapi" not in duplicate
    assert "token" not in duplicate["provider"]
    duplicate["provider"]["safe"] = False
    assert original["provider"]["safe"] is True


def test_duplicate_collision_and_optional_key_path():
    original = {"name": "Cluster", "username": "alice", "private_key_path": "C:/key", "account": "proj"}
    duplicate = duplicate_profile(original, ["Cluster", "Cluster (copy)"])
    assert duplicate["name"] == "Cluster (copy) 2"
    assert duplicate["username"] == "alice"
    assert duplicate["account"] == "proj"
    assert "private_key_path" not in duplicate
    kept = duplicate_profile(original, copy_key_path=True)
    assert kept["private_key_path"] == original["private_key_path"]
