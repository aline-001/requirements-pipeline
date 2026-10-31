#!/usr/bin/env bash
# Baserow -> StrictDoc -> Pull Request (Task 4)
#
#   Manual run:     ./run_sync.sh
#   Scheduled run:  crontab -e   and add
#                   15 6 * * *  cd $HOME/requirements-pipeline && ./run_sync.sh >> logs/sync.log 2>&1
#
# Each run:
#   1. updates main and marks requirements that are already merged on main as Baselined in Baserow
#   2. exports approved needs/requirements to docs/sdoc/*.sdoc (fails on broken links,
#      duplicate IDs, requirements with no need)
#   3. checks the files with StrictDoc itself
#   4. if anything changed, pushes a sync/<timestamp> branch and opens a Pull Request.
#      Merging that Pull Request is the baseline; the next run marks it Baselined.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
export PATH="$HOME/.local/bin:$PATH"   # strictdoc installed with pipx
STAMP="$(date -u +%Y%m%d-%H%M%S)"
echo "=== sync $STAMP ==="

git checkout -q main
git pull -q --ff-only

python3 sync/sync.py baseline
python3 sync/sync.py export

# StrictDoc must accept the files before anything is pushed.
strictdoc export . --output-dir /tmp/strictdoc-check > /tmp/strictdoc-check.log 2>&1 || {
  echo "StrictDoc rejected the generated files:"; tail -20 /tmp/strictdoc-check.log; exit 1; }

if [ -z "$(git status --porcelain -- docs/sdoc)" ]; then
  echo "No requirement changes."
  exit 0
fi

BRANCH="sync/$STAMP"
git checkout -q -b "$BRANCH"
trap 'git checkout -q main' EXIT   # always return to main, even on failure
git add -A docs/sdoc
git commit -q -m "sync: requirements from Baserow ($STAMP)"
git push -q -u origin "$BRANCH"

TITLE="Requirements sync $STAMP"
BODY="Automated export of approved requirements from Baserow.

$(git diff --stat main -- docs/sdoc)

Merging this Pull Request creates the baseline. The next sync run marks the merged requirements as Baselined in Baserow."
if ! { command -v gh >/dev/null 2>&1 && gh pr create --base main --head "$BRANCH" --title "$TITLE" --body "$BODY"; }; then
  REPO_URL="$(git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)#https://github.com/#; s#\.git$##')"
  echo "Open the Pull Request: $REPO_URL/compare/main...$BRANCH?expand=1"
fi
