#!/bin/sh
# install-difyctl.sh: install or upgrade difyctl with Dify's official installer.
#
# This is a thin wrapper. The real work is done by the installer published in
# langgenius/dify (cli/scripts/install-cli.sh), which downloads the release
# asset for this OS/arch, checks its sha256, and writes it to ~/.local/bin.
#
# It installs the latest release. difyctl gets its business commands from the
# server's catalog at run time, so there is no need to match the server version.
#
# Env passed through unchanged: DIFY_VERSION, DIFYCTL_VERSION, DIFYCTL_INSTALL_DIR, DIFYCTL_PREFIX, GITHUB_TOKEN/GH_TOKEN.
#
# Windows: run this in PowerShell instead:
#   irm https://raw.githubusercontent.com/langgenius/dify/main/cli/scripts/install.ps1 | iex
set -eu

URL="${DIFYCTL_INSTALLER_URL:-https://raw.githubusercontent.com/langgenius/dify/main/cli/scripts/install-cli.sh}"

command -v curl >/dev/null 2>&1 || { echo "install-difyctl: curl is required" >&2; exit 1; }

tmp="${TMPDIR:-/tmp}/difyctl-installer.$$.sh"
trap 'rm -f "$tmp"' EXIT INT TERM

curl -fsSL "$URL" -o "$tmp"
sh "$tmp"

dir="${DIFYCTL_INSTALL_DIR:-${DIFYCTL_PREFIX:-$HOME/.local}/bin}"
case ":$PATH:" in
  *":$dir:"*) ;;
  *) echo "install-difyctl: note: $dir is not on PATH. Call difyctl as $dir/difyctl, or add $dir to PATH." >&2 ;;
esac
