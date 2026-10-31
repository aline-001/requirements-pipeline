#!/usr/bin/env bash
# Rebuild the published site from main (Task 5): RTM + coverage + StrictDoc export.
# Everything is computed from the repository; nothing is edited by hand.
#
#   Manual run:     ./publish.sh
#   Scheduled run:  */30 * * * *  cd $HOME/requirements-pipeline && ./publish.sh >> logs/publish.log 2>&1
#
# The site/ folder is served read-only by rtm-site.service on 127.0.0.1:8090
# and exposed through the Cloudflare tunnel (see README).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
export PATH="$HOME/.local/bin:$PATH"

git checkout -q main
git pull -q --ff-only

rm -rf build/site && mkdir -p build/site
python3 rtm.py --out build/site
strictdoc export . --output-dir build/strictdoc > logs/strictdoc-export.log 2>&1
cp -r build/strictdoc/html build/site/strictdoc

# Swap in atomically so the site never shows a half-built state.
rm -rf site.old && { [ -d site ] && mv site site.old || true; } && mv build/site site && rm -rf site.old
echo "Published $(date -u '+%Y-%m-%d %H:%M UTC') from $(git rev-parse --short HEAD)"
