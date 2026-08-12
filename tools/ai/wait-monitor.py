"""Wait for one OpenCode monitoring interval, then exit successfully."""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wait before the next OpenCode/DeepSeek status check."
    )
    parser.add_argument(
        "--minutes",
        type=float,
        default=5.0,
        help="Monitoring interval in minutes (default: 5; use 10 or 15 for long work).",
    )
    args = parser.parse_args()
    if args.minutes <= 0:
        parser.error("--minutes must be greater than zero")

    started_at = datetime.now().astimezone()
    finished_at = started_at + timedelta(minutes=args.minutes)
    print(f"wait_started_at={started_at.isoformat()}", flush=True)
    print(f"wait_until={finished_at.isoformat()}", flush=True)
    time.sleep(args.minutes * 60)
    print(f"wait_finished_at={datetime.now().astimezone().isoformat()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
