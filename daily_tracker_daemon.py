"""
Daily Top-5 Recommendation Autonomous Tracker & GX10 24/7 Daemon
Executes continuous empirical logging of top-ranked sector recommendations
into SQLite WAL database (data/simulated_diary.db) without requiring UI interaction.

Usage:
  # Run immediate one-shot snapshot of all core sectors:
  python daily_tracker_daemon.py --run-now

  # Run 24/7 background service on ASUS GX10 workstation:
  python daily_tracker_daemon.py --daemon --interval 1800
"""

import os
import sys
import uuid
import signal
import argparse
import datetime
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(_REPO_ROOT / ".env")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import rubberband_engine_v3 as rbe3
import diary_db

HEARTBEAT_PATH = _REPO_ROOT / "data" / ".daemon_heartbeat"

_STOP_EVENT = threading.Event()
_WORKER_BUSY_LOCK = threading.Lock()
_BACKUP_LOCK = threading.Lock()
_LAST_DAILY_BACKUP_DATE: Optional[str] = None


def write_heartbeat(status: str = "alive") -> None:
    """Atomically writes daemon heartbeat timestamp to data/.daemon_heartbeat for Docker/systemd healthchecks."""
    tmp_path: Optional[Path] = None
    try:
        HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = f"{now_utc} status={status}\n"
        tmp_path = HEARTBEAT_PATH.parent / f".daemon_heartbeat.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, HEARTBEAT_PATH)
    except Exception as e:
        print(f"[Daemon Heartbeat Warning] {e}", flush=True)
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _run_daily_backup_and_checkpoint(today_str: str, force: bool = False) -> None:
    """Runs online daily diary backup + WAL checkpoint once per trading day (or when forced)."""
    global _LAST_DAILY_BACKUP_DATE
    with _BACKUP_LOCK:
        if not force and _LAST_DAILY_BACKUP_DATE == today_str:
            return
        try:
            backup_path = diary_db.backup_diary_db(tag="daily")
            diary_db.checkpoint_wal()
            _LAST_DAILY_BACKUP_DATE = today_str
            print(
                f"  [OK] Daily diary backup ({backup_path or 'skipped'}) & WAL checkpoint complete.",
                flush=True,
            )
        except Exception as e:
            print(f"  [WARN] Daily diary backup/checkpoint error: {e}", flush=True)


def _is_valid_snapshot_window(ny_now: Optional[datetime.datetime] = None) -> bool:
    """
    Returns True only on Wall Street weekdays (Mon-Fri) after 09:45 America/New_York,
    preventing stale 00:01 AM overnight captures and weekend snapshot stamps.
    """
    dt = ny_now or rbe3.get_ny_now()
    if dt.weekday() >= 5:
        return False
    return (dt.hour > 9) or (dt.hour == 9 and dt.minute >= 45)


def capture_all_sectors_snapshot(force: bool = False) -> Dict[str, int]:
    """
    Scans all core sectors, runs Two-Stage Top-5 Vetting, and archives the
    results into the persistent diary database under Wall Street trading date.
    Triggers daily online backup + WAL checkpoint after snapshot capture.
    """
    write_heartbeat("scanning")
    ny_now = rbe3.get_ny_now()
    today_str = ny_now.date().strftime("%Y-%m-%d")
    results: Dict[str, int] = {}
    sectors = list(rbe3.SECTORS.keys())
    saved_fresh = False

    print(
        f"[{ny_now.strftime('%Y-%m-%d %H:%M:%S ET')}] Starting Top-5 Sector Snapshot ({len(sectors)} sectors) for {today_str}...",
        flush=True,
    )

    for sec in sectors:
        if _STOP_EVENT.is_set():
            break
        if not force and diary_db.has_snapshot_for_date(today_str, sec):
            print(f"  [OK] Sector '{sec}' already archived for {today_str}. Skipping.", flush=True)
            results[sec] = 5
            continue

        try:
            print(f"  [...] Evaluating sector '{sec}' (Top 5 Deep-Vetted)...", flush=True)
            cands = rbe3.get_ranked_sector_candidates(sec, top_n_vet=5)
            count = diary_db.save_top5_snapshot(sec, cands, snapshot_date=today_str)
            results[sec] = count
            if count > 0:
                saved_fresh = True
            print(f"  [OK] Sector '{sec}': {count} recommendations archived.", flush=True)
        except Exception as e:
            print(f"  [FAIL] Error evaluating sector '{sec}': {e}", flush=True)
            results[sec] = 0

    _run_daily_backup_and_checkpoint(today_str, force=force or saved_fresh)
    write_heartbeat("idle")
    print(
        f"[{rbe3.get_ny_now().strftime('%Y-%m-%d %H:%M:%S ET')}] Top-5 Snapshot complete. Total sectors processed: {len(results)}.",
        flush=True,
    )
    return results


def _handle_shutdown_signal(signum: int, _frame: Any) -> None:
    print(f"[Daemon] Received signal {signum}; shutting down gracefully...", flush=True)
    _STOP_EVENT.set()


def run_daemon_loop(check_interval_seconds: int = 1800) -> None:
    """
    Continuous background loop for 24/7 execution on the ASUS GX10 workstation.
    Captures daily snapshots once per trading day during/after cash session (>= 09:45 ET),
    writes a heartbeat on startup and every cycle, and runs daily DB backups + WAL checkpoints.
    """
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_shutdown_signal)
        except Exception:
            pass

    _STOP_EVENT.clear()
    interval = max(60, int(check_interval_seconds))
    write_heartbeat("startup")
    print(f"Starting 24/7 GX10 Top-5 Recommendation Daemon (Polling every {interval}s)...", flush=True)
    try:
        while not _STOP_EVENT.is_set():
            write_heartbeat("polling")
            try:
                ny_now = rbe3.get_ny_now()
                if _is_valid_snapshot_window(ny_now):
                    capture_all_sectors_snapshot(force=False)
            except Exception as e:
                print(f"[Daemon Error] {e}", flush=True)

            write_heartbeat("sleeping")
            _STOP_EVENT.wait(interval)
    finally:
        diary_db.checkpoint_wal()
        write_heartbeat("stopped")


def auto_snapshot_background_worker() -> None:
    """
    Non-blocking background helper called once on app startup.
    Checks if today's NY trading-day snapshot is missing (weekdays >= 09:45 ET) and archives it.
    """
    def _worker() -> None:
        if not _WORKER_BUSY_LOCK.acquire(blocking=False):
            return
        try:
            ny_now = rbe3.get_ny_now()
            if not _is_valid_snapshot_window(ny_now):
                return
            today_str = ny_now.date().strftime("%Y-%m-%d")
            saved_any = False
            for sec in rbe3.SECTORS.keys():
                if not diary_db.has_snapshot_for_date(today_str, sec):
                    try:
                        cands = rbe3.get_ranked_sector_candidates(sec, top_n_vet=5)
                        if diary_db.save_top5_snapshot(sec, cands, snapshot_date=today_str) > 0:
                            saved_any = True
                    except Exception:
                        pass
            if saved_any:
                _run_daily_backup_and_checkpoint(today_str, force=False)
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
