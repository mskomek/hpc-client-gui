from pathlib import Path


def test_language_is_loaded_before_splash_and_statuses_are_translated():
    source = (Path(__file__).resolve().parents[1] / "src" / "hpc_gui" / "app.py").read_text(encoding="utf-8")

    assert source.index("load_saved_language(") < source.index("StartupSplash()")
    for key in ("status_preparing", "status_checking", "status_loading"):
        assert f't("splash.{key}")' in source
