#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Time Tracker — installer
# Works for any macOS user. Safe to re-run.
#
# Run from the folder containing tracker.py:
#   bash install.sh
# ─────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.timetracker"
PLIST_LABEL="com.$(whoami).timetracker"
PLIST_FILE="${PLIST_LABEL}.plist"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "──────────────────────────────────────────"
echo "  Time Tracker — installer"
echo "──────────────────────────────────────────"

# 1. Create tracker directory
mkdir -p "$INSTALL_DIR"

# 2. Copy the tracker script
cp "$SCRIPT_DIR/tracker.py" "$INSTALL_DIR/tracker.py"
chmod +x "$INSTALL_DIR/tracker.py"
echo "✓  Installed tracker.py → $INSTALL_DIR/"

# 3. Generate and install the launchd plist (no hardcoded paths)
mkdir -p "$LAUNCH_AGENTS"
cat > "$LAUNCH_AGENTS/$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${INSTALL_DIR}/tracker.py</string>
        <string>poll</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${INSTALL_DIR}/tracker.log</string>
    <key>StandardErrorPath</key>
    <string>${INSTALL_DIR}/tracker.log</string>
</dict>
</plist>
EOF

launchctl unload "$LAUNCH_AGENTS/$PLIST_FILE" 2>/dev/null || true
launchctl load  "$LAUNCH_AGENTS/$PLIST_FILE"
echo "✓  launchd agent loaded (polls every 5 minutes, auto-starts on login)"

# 4. Add/update the 'track' alias in shell configs
ALIAS_LINE="alias track='python3 \$HOME/.timetracker/tracker.py --cwd \"\$PWD\"'"

update_alias() {
    local rc_file="$1"
    [ -f "$rc_file" ] || return
    sed -i.bak '/alias track=/d' "$rc_file" && rm -f "${rc_file}.bak"
    sed -i.bak '/^# Time tracker$/d' "$rc_file" && rm -f "${rc_file}.bak"
    printf '\n# Time tracker\n%s\n' "$ALIAS_LINE" >> "$rc_file"
    echo "✓  Updated 'track' alias in $rc_file"
}

update_alias "$HOME/.zshrc"
update_alias "$HOME/.bashrc"

echo ""
echo "──────────────────────────────────────────"
echo "  Done! Reload your shell:"
echo "    source ~/.zshrc"
echo ""
echo "  Then start tracking a project:"
echo "    cd /path/to/your/project"
echo "    track add"
echo ""
echo "  Commands:"
echo "    track add             — track current folder"
echo "    track add <path>      — track a specific folder"
echo "    track remove          — stop tracking current folder"
echo "    track list            — show all tracked projects"
echo "    track today           — today's time (current folder)"
echo "    track week            — last 7 days  (current folder)"
echo "    track month           — this month   (current folder)"
echo "    track all             — all time     (current folder)"
echo ""
echo "  Data: $INSTALL_DIR/"
echo "  Log:  $INSTALL_DIR/tracker.log"
echo "──────────────────────────────────────────"
