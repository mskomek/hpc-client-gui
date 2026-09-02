from pathlib import Path

from hpc_gui.services.parity_matrix import render_status


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    baseline = (ROOT / "docs" / "v2" / "GUI_FEATURE_PARITY_BASELINE.md").read_text(encoding="utf-8")
    (ROOT / "docs" / "v2" / "V2_PARITY_STATUS.md").write_text(render_status(baseline), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
