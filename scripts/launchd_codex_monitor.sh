#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"
LABEL="${CODEX_MONITOR_LABEL:-com.bojxai.codex-monitor}"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
OUT_LOG="$LOG_DIR/codex-monitor.launchd.out.log"
ERR_LOG="$LOG_DIR/codex-monitor.launchd.err.log"

BASE_URL="${CODEX_APP_BASE_URL:-http://127.0.0.1:8000/api/v1}"
BEARER_TOKEN="${CODEX_APP_BEARER_TOKEN:-}"
ALERT_THRESHOLD="${CODEX_MONITOR_ALERT_THRESHOLD:-2}"
TIMEOUT_SEC="${CODEX_MONITOR_TIMEOUT_SEC:-8}"
CHECK_MINIO="${CODEX_MONITOR_CHECK_MINIO:-0}"
CHECK_CODEX="${CODEX_MONITOR_CHECK_CODEX:-0}"
INTERVAL_SEC="${CODEX_MONITOR_INTERVAL_SEC:-180}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

write_plist() {
  cat >"$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${ROOT_DIR}/scripts/cron/codex_app_monitor.sh</string>
$(if [[ "$CHECK_CODEX" == "1" ]]; then echo '    <string>--check-codex</string>'; fi)
$(if [[ "$CHECK_MINIO" == "1" ]]; then echo '    <string>--check-minio</string>'; fi)
  </array>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHON_BIN</key>
    <string>${PYTHON_BIN}</string>
    <key>CODEX_APP_BASE_URL</key>
    <string>${BASE_URL}</string>
    <key>CODEX_MONITOR_ALERT_THRESHOLD</key>
    <string>${ALERT_THRESHOLD}</string>
    <key>CODEX_MONITOR_TIMEOUT_SEC</key>
    <string>${TIMEOUT_SEC}</string>
    <key>CODEX_APP_BEARER_TOKEN</key>
    <string>${BEARER_TOKEN}</string>
  </dict>

  <key>WorkingDirectory</key>
  <string>${ROOT_DIR}</string>

  <key>RunAtLoad</key>
  <true/>

  <key>StartInterval</key>
  <integer>${INTERVAL_SEC}</integer>

  <key>StandardOutPath</key>
  <string>${OUT_LOG}</string>

  <key>StandardErrorPath</key>
  <string>${ERR_LOG}</string>
</dict>
</plist>
PLIST
}

launchd_bootout() {
  launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
  launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
}

launchd_bootstrap() {
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || launchctl load "$PLIST_PATH"
  launchctl enable "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
  launchctl kickstart -k "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
}

status_job() {
  if [[ ! -f "$PLIST_PATH" ]]; then
    echo "not installed: $PLIST_PATH"
    return 1
  fi

  echo "plist: $PLIST_PATH"
  launchctl print "gui/$(id -u)/${LABEL}" 2>/dev/null | sed -n '1,80p' || launchctl list | grep "$LABEL" || true
  echo "out_log: $OUT_LOG"
  echo "err_log: $ERR_LOG"
}

case "$ACTION" in
  install)
    write_plist
    launchd_bootout
    launchd_bootstrap
    echo "installed and started: $LABEL"
    status_job || true
    ;;
  uninstall)
    launchd_bootout
    rm -f "$PLIST_PATH"
    echo "uninstalled: $LABEL"
    ;;
  restart)
    if [[ ! -f "$PLIST_PATH" ]]; then
      write_plist
    fi
    launchd_bootout
    launchd_bootstrap
    echo "restarted: $LABEL"
    ;;
  status)
    status_job
    ;;
  tail)
    tail -n 80 -f "$OUT_LOG" "$ERR_LOG"
    ;;
  *)
    echo "usage: $0 {install|uninstall|restart|status|tail}" >&2
    exit 2
    ;;
esac
