"""
Daily Top-5 Recommendation Autonomous Tracker & GX10 24/7 Daemon
Executes continuous empirical logging of top-ranked sector recommendations
into SQLite WAL database (data/simulated_diary.db) without requiring UI interaction.

Usage:
  # Run immediate one-shot snapshot of all 4 sectors:
  python daily_tracker_daemon.py --run-now

  # Run 24/7 background service on ASUS GX10 workstation:
  python daily_tracker_daemon.py --daemon --interval 1800
"""

import sys
import time
import argparse
import datetime
import threading
from typing import Dict, Any, List

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import rubberband_engine_v3 as rbe3
import diary_db


def capture_all_sectors_snapshot(force: bool = False) -> Dict[str, int]:
    """
    Scans all 4 core sectors, runs Two-Stage Top-5 Vetting, and archives the
    results into the persistent diary database.
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    results = {}
    sectors = list(rbe3.SECTORS.keys())

    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Top-5 Sector Snapshot for {today_str}...")

    for sec in sectors:
        if not force and diary_db.has_snapshot_for_date(today_str, sec):
            print(f"  [OK] Sector '{sec}' already archived for {today_str}. Skipping.")
            results[sec] = 5
            continue

        try:
            print(f"  [...] Evaluating sector '{sec}' (Top 5 Deep-Vetted)...")
            cands = rbe3.get_ranked_sector_candidates(sec, top_n_vet=5)
            count = diary_db.save_top5_snapshot(sec, cands, snapshot_date=today_str)
            results[sec] = count
            print(f"  [OK] Sector '{sec}': {count} recommendations archived.")
        except Exception as e:
            print(f"  [FAIL] Error evaluating sector '{sec}': {e}")
            results[sec] = 0

    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Top-5 Snapshot complete. Total sectors processed: {len(results)}.")
    return results


def run_daemon_loop(check_interval_seconds: int = 1800):
    """
    Continuous background loop for 24/7 execution on the ASUS GX10 workstation.
    Captures daily snapshots once per trading day around market close or when new day starts.
    """
    print(f"Starting 24/7 GX10 Top-5 Recommendation Daemon (Polling every {check_interval_seconds}s)...")
    while True:
        try:
            ny_now = rbe3.get_ny_now()
            # On weekdays, guarantee snapshot is taken during market hours or post-close
            if ny_now.weekday() < 5:
                capture_all_sectors_snapshot(force=False)
        except Exception as e:
            print(f"[Daemon Error] {e}")

        time.sleep(check_interval_seconds)


_WORKER_BUSY_LOCK = threading.Lock()


def auto_snapshot_background_worker():
    """
    Non-blocking background helper called on startup.
    Checks if today's snapshot is missing and archives it without slowing down the UI.
    Guarantees no overlapping background workers via reentrancy lock.
    """
    def _worker():
        if not _WORKER_BUSY_LOCK.acquire(blocking=False):
            return  # Another worker is already actively taking a snapshot
        try:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            for sec in rbe3.SECTORS.keys():
                if not diary_db.has_snapshot_for_date(today_str, sec):
                    try:
                        cands = rbe3.get_ranked_sector_candidates(sec, top_n_vet=5)
                        diary_db.save_top5_snapshot(sec, cands, snapshot_date=today_str)
                    except Exception:
                        pass
        finally:
            _WORKER_BUSY_LOCK.release()

    t = threading.Thread(target=_worker, daemon=True, name="DailyTrackerWorker")
    t.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Top-5 Recommendation Tracker Daemon")
    parser.add_argument("--run-now", action="store_true", help="Execute immediate snapshot across all sectors")
    parser.add_argument("--force", action="store_true", help="Force overwrite today's snapshot if already present")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as a 24/7 background service")
    parser.add_argument("--interval", type=int, default=1800, help="Daemon check interval in seconds (default: 1800)")

    args = parser.parse_args()

    if args.daemon:
        run_daemon_loop(check_interval_seconds=args.interval)
    elif args.run_now or not sys.argv[1:]:
        capture_all_sectors_snapshot(force=args.force)
