#!/usr/bin/env python3
"""
Multi-project time tracker.
Polls every 5 minutes via launchd and logs active work time per project.

Usage (via 'track' alias — see install.sh):
  track add [path]    — start tracking current folder (or given path)
  track remove [path] — stop tracking current folder (or given path)
  track list          — show all tracked projects
  track today         — today's time for current folder's project
  track week          — last 7 days for current folder's project
  track month         — this month for current folder's project
  track all           — all recorded days for current folder's project

  track poll          — called automatically by launchd (not for manual use)
"""

import os
import re
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, Tuple

TRACKER_DIR   = Path.home() / ".timetracker"
PROJECTS_FILE = TRACKER_DIR / "projects.json"
POLL_MINUTES  = 5
LOOKBACK_SECS = 360   # 6 min — slight buffer over the 5-min poll interval

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".next",
    "dist", "build", ".venv", "venv", ".cache", ".tox",
}


# ── Storage helpers ───────────────────────────────────────────────────────────

def slugify(path: str) -> str:
    """Derive a safe filename from a directory path."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", Path(path).name)


def data_file(project_path: str) -> Path:
    projects = load_projects()
    slug = projects.get(project_path, slugify(project_path))
    return TRACKER_DIR / f"{slug}.json"


def load_projects() -> dict:
    """Return {absolute_path: slug} dict."""
    if PROJECTS_FILE.exists():
        with open(PROJECTS_FILE) as f:
            return json.load(f)
    return {}


def save_projects(projects: dict):
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


def load_data(project_path: str) -> dict:
    f = data_file(project_path)
    if f.exists():
        with open(f) as fp:
            return json.load(fp)
    return {}


def save_data(project_path: str, data: dict):
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    with open(data_file(project_path), "w") as f:
        json.dump(data, f, indent=2)


# ── Utilities ─────────────────────────────────────────────────────────────────

def fmt(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h == 0: return f"{m}m"
    if m == 0: return f"{h}h"
    return f"{h}h {m}m"


def was_recently_modified(directory: str) -> bool:
    now = time.time()
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            try:
                if now - os.path.getmtime(os.path.join(root, fname)) < LOOKBACK_SECS:
                    return True
            except OSError:
                pass
    return False


def find_project_for_cwd(cwd: str, projects: dict) -> Optional[str]:
    """
    Return the tracked project path that best matches cwd.
    Supports exact matches and sub-directory matches.
    """
    cwd = str(Path(cwd).resolve())
    # Exact match
    if cwd in projects:
        return cwd
    # cwd is inside a tracked project
    for p in sorted(projects, key=len, reverse=True):   # longest match first
        resolved = str(Path(p).resolve())
        if cwd.startswith(resolved + os.sep) or cwd == resolved:
            return p
    return None


def require_project(cwd: str) -> Tuple[str, dict]:
    """Exit with a helpful message if cwd isn't inside a tracked project."""
    projects = load_projects()
    project = find_project_for_cwd(cwd, projects)
    if not project:
        print(f"No tracked project found for: {cwd}")
        print("  → Run 'track add' to track this folder.")
        print("  → Run 'track list' to see all tracked projects.")
        sys.exit(0)
    return project, load_data(project)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_add(path: Optional[str], cwd: str):
    projects = load_projects()
    target = str(Path(path or cwd).resolve())
    if not Path(target).is_dir():
        print(f"Error: '{target}' is not a directory.")
        sys.exit(1)
    if target in projects:
        print(f"Already tracking: {target}")
        return
    slug = slugify(target)
    # Avoid slug collisions
    existing_slugs = set(projects.values())
    base, suffix = slug, 2
    while slug in existing_slugs:
        slug = f"{base}_{suffix}"
        suffix += 1
    projects[target] = slug
    save_projects(projects)
    print(f"✓ Now tracking: {target}")
    print(f"  Data file: {TRACKER_DIR / (slug + '.json')}")


def cmd_remove(path: Optional[str], cwd: str):
    projects = load_projects()
    if path:
        target = str(Path(path).resolve())
    else:
        target = find_project_for_cwd(cwd, projects)
    if not target or target not in projects:
        print("No tracked project found for that path.")
        print("  → Run 'track list' to see tracked projects.")
        sys.exit(1)
    name = Path(target).name
    del projects[target]
    save_projects(projects)
    print(f"✓ Stopped tracking: {target}")
    print(f"  (Historical data kept at: {TRACKER_DIR / (slugify(target) + '.json')})")


def cmd_list():
    projects = load_projects()
    if not projects:
        print("No projects tracked yet.  Run 'track add' inside a project folder.")
        return
    today = str(date.today())
    print(f"Tracked projects ({len(projects)}):")
    for path in sorted(projects):
        data = load_data(path)
        mins_today = data.get(today, 0)
        exists = "✓" if Path(path).is_dir() else "✗ (folder missing)"
        today_str = f"today: {fmt(mins_today)}" if mins_today else "no activity today"
        print(f"  {exists}  {Path(path).name}")
        print(f"       {path}")
        print(f"       {today_str}")


def cmd_poll():
    projects = load_projects()
    if not projects:
        return
    ts = datetime.now().strftime("%H:%M")
    for project_path in list(projects):
        if not Path(project_path).is_dir():
            continue
        if was_recently_modified(project_path):
            data = load_data(project_path)
            today = str(date.today())
            data[today] = data.get(today, 0) + POLL_MINUTES
            save_data(project_path, data)
            print(f"[{ts}] {Path(project_path).name}: active — +5 min (today: {fmt(data[today])})")
        else:
            print(f"[{ts}] {Path(project_path).name}: no recent activity")


def cmd_today(cwd: str):
    project, data = require_project(cwd)
    today = date.today()
    mins = data.get(str(today), 0)
    print(f"{Path(project).name} — Today ({today.strftime('%A %b %d')}): "
          f"{fmt(mins) if mins else 'no time logged yet'}")


def cmd_week(cwd: str):
    project, data = require_project(cwd)
    today = date.today()
    print(f"{Path(project).name} — Last 7 days:")
    total = 0
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        mins = data.get(str(d), 0)
        total += mins
        label = "Today     " if i == 0 else d.strftime("%a %b %d  ")
        bar = "█" * (mins // 30)
        print(f"  {label}  {fmt(mins):>6}  {bar}")
    print(f"  {'─' * 20}")
    print(f"  Total              {fmt(total)}")


def cmd_month(cwd: str):
    project, data = require_project(cwd)
    today = date.today()
    print(f"{Path(project).name} — {today.strftime('%B %Y')}:")
    total = 0
    for key, mins in sorted(data.items()):
        d = date.fromisoformat(key)
        if d.year == today.year and d.month == today.month:
            total += mins
            label = "Today     " if d == today else d.strftime("%a %b %d  ")
            bar = "█" * (mins // 30)
            print(f"  {label}  {fmt(mins):>6}  {bar}")
    print(f"  {'─' * 20}")
    print(f"  Total              {fmt(total)}")


def cmd_all(cwd: str):
    project, data = require_project(cwd)
    if not data:
        print(f"{Path(project).name}: No data recorded yet.")
        return
    print(f"{Path(project).name} — All time:")
    total = 0
    for key, mins in sorted(data.items()):
        print(f"  {key}  {fmt(mins)}")
        total += mins
    print(f"  {'─' * 20}")
    print(f"  Total              {fmt(total)}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?", default="today")
    parser.add_argument("arg",     nargs="?", default=None)
    parser.add_argument("--cwd",   default=os.getcwd())
    args = parser.parse_args()

    cmd = args.command
    cwd = args.cwd

    if cmd == "poll":
        cmd_poll()
    elif cmd == "add":
        cmd_add(args.arg, cwd)
    elif cmd == "remove":
        cmd_remove(args.arg, cwd)
    elif cmd == "list":
        cmd_list()
    elif cmd == "today":
        cmd_today(cwd)
    elif cmd == "week":
        cmd_week(cwd)
    elif cmd == "month":
        cmd_month(cwd)
    elif cmd == "all":
        cmd_all(cwd)
    else:
        print(f"Unknown command: '{cmd}'")
        print("Commands: add, remove, list, today, week, month, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
