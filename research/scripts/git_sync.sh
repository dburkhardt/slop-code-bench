#!/bin/bash
# git_sync.sh — Commit and push outputs/ and research/ periodically.
#
# Designed to run from cron every 15 minutes. Handles no-changes
# gracefully (no empty commits). Exits 0 even when there is nothing
# to commit, so cron does not send error mail.
#
# Usage:
#   bash research/scripts/git_sync.sh
#
# Cron entry (installed by this project):
#   */15 * * * * cd /home/ubuntu/git-repos/slop-code-bench && bash research/scripts/git_sync.sh >> /tmp/git_sync.log 2>&1

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

# Stage only the directories we care about.
git add --all -- outputs/ research/

# Check whether there are staged changes. If not, exit cleanly.
if git diff --cached --quiet; then
    echo "[$TIMESTAMP] git_sync: nothing to commit"
    exit 0
fi

git commit -m "auto: sync experiment outputs"
echo "[$TIMESTAMP] git_sync: committed"

# Push if a remote is configured; tolerate push failures so cron
# does not alarm on transient network issues.
if git remote get-url origin >/dev/null 2>&1; then
    git push origin main 2>&1 || echo "[$TIMESTAMP] git_sync: push failed (will retry next cycle)"
else
    echo "[$TIMESTAMP] git_sync: no remote configured, skipping push"
fi
