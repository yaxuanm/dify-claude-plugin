#!/bin/sh
# difyctl-status.sh: report whether difyctl is installed and where.
# Prints one JSON object on stdout. Never logs in, never changes anything.
#
#   {"installed": true, "path": "/home/me/.local/bin/difyctl",
#    "on_path": true, "version": "...", "skill_install_supported": true}
set -u

json_str() {
  # Minimal JSON string escaper for paths and version lines.
  printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr -d '\n\r')"
}

bin=""
on_path=false
if command -v difyctl >/dev/null 2>&1; then
  bin=$(command -v difyctl)
  on_path=true
else
  # Default install dirs used by the official installers.
  for c in "${DIFYCTL_INSTALL_DIR:-}/difyctl" "${DIFYCTL_PREFIX:-$HOME/.local}/bin/difyctl" "$HOME/.local/bin/difyctl"; do
    if [ -x "$c" ]; then bin="$c"; break; fi
  done
fi

if [ -z "$bin" ]; then
  printf '{"installed": false, "path": null, "on_path": false, "version": null, "skill_install_supported": false}\n'
  exit 0
fi

raw=$("$bin" version 2>/dev/null | tr -d '\n\r')
# Newer difyctl prints JSON over several lines; take the first "version" value.
ver=$(printf '%s' "$raw" | grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n 1 | sed 's/.*"\([^"]*\)"$/\1/')
[ -n "$ver" ] || ver=$(printf '%s' "$raw" | cut -c1-80)
skills=false
if "$bin" install skills --help >/dev/null 2>&1; then skills=true; fi

printf '{"installed": true, "path": %s, "on_path": %s, "version": %s, "skill_install_supported": %s}\n' \
  "$(json_str "$bin")" "$on_path" "$(json_str "$ver")" "$skills"
