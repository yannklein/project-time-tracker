# Time Tracker

A lightweight, automatic work-time tracker for macOS. It watches project folders for file changes and logs how long you work on them — no manual start/stop needed.

## How it works

A background job runs every 5 minutes via macOS's built-in `launchd` scheduler. It checks whether any file in your tracked project folders was modified in the last 5 minutes. If yes, 5 minutes are added to that day's total. The job exits immediately after — it uses no memory between runs.

**Accuracy:** ±5 minutes. More than enough for daily totals.
**Overhead:** ~0% CPU, 0 MB RAM at rest.

---

## Requirements

- macOS (uses launchd)
- Python 3 (pre-installed on macOS)

---

## Installation

```bash
bash install.sh
```

Then reload your shell:

```bash
source ~/.zshrc   # or source ~/.bashrc
```

The installer:
- Copies `tracker.py` to `~/.timetracker/`
- Registers a launchd agent that polls every 5 minutes and auto-starts on login
- Adds a `track` command alias to your shell config

---

## Package contents

| File | Description |
|---|---|
| `tracker.py` | Main script — handles polling and all CLI commands |
| `install.sh` | One-shot installer, safe to re-run |
| `README.md` | This file |

After installation, data is stored in `~/.timetracker/`:

| File | Description |
|---|---|
| `projects.json` | Registry of tracked project folders |
| `<project-name>.json` | Recorded work time for each project (one file per project) |
| `tracker.log` | Polling activity log (useful for debugging) |

---

## Commands

All commands are context-aware: they detect which tracked project your current folder belongs to.

### Managing projects

```bash
track add                  # start tracking the current folder
track add /path/to/project # start tracking a specific folder
track remove               # stop tracking the current folder
track list                 # show all tracked projects and today's activity
```

### Viewing your time

```bash
track today    # time logged today for the current folder's project
track week     # last 7 days with a bar chart
track month    # this calendar month
track all      # every recorded day since tracking started
```

If you run a summary command from a folder that isn't tracked, you'll get a message telling you so.

### Example output

```
my-project — Last 7 days:
  Mon Mar 11    1h 30m  ███
  Tue Mar 12    2h      ████
  Wed Mar 13    0m
  Thu Mar 14    3h 30m  ███████
  Fri Mar 15    1h      ██
  Sat Mar 16    0m
  Today           45m   █
  ────────────────────
  Total           8h 45m
```

Each `█` block represents 30 minutes.

---

## Uninstalling

```bash
# Stop and remove the launchd agent
launchctl unload ~/Library/LaunchAgents/com.$(whoami).timetracker.plist
rm ~/Library/LaunchAgents/com.$(whoami).timetracker.plist

# Remove tracker files (and data — skip the last line to keep your history)
rm ~/Library/LaunchAgents/com.$(whoami).timetracker.plist
rm -rf ~/.timetracker

# Remove the alias from your shell config
# Delete the two lines containing "Time tracker" and "alias track=" from ~/.zshrc
```
