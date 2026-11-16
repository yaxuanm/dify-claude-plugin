#!/bin/sh
# sync-difyctl-skill.sh: refresh skills/difyctl/ from langgenius/dify.
#
# The difyctl skill is maintained upstream in langgenius/dify (skills/difyctl).
# This plugin ships a copy so it works without an extra install step. Run this
# before each release, review the diff, and bump the version in
# .claude-plugin/plugin.json and .claude-plugin/marketplace.json.
#
# usage: sh scripts/sync-difyctl-skill.sh [git-ref]   (default: main)
set -eu

REF="${1:-main}"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM

git clone --quiet --depth 1 --branch "$REF" --filter=blob:none --sparse \
  https://github.com/langgenius/dify.git "$TMP/dify"
git -C "$TMP/dify" sparse-checkout set skills/difyctl
SHA=$(git -C "$TMP/dify" rev-parse HEAD)

rm -rf "$ROOT/skills/difyctl"
cp -R "$TMP/dify/skills/difyctl" "$ROOT/skills/difyctl"

# Record where the copy came from.
sed -i.bak "s/^difyctl skill commit: .*/difyctl skill commit: $SHA/" "$ROOT/NOTICE" && rm -f "$ROOT/NOTICE.bak"
echo "synced skills/difyctl from langgenius/dify@$SHA"
