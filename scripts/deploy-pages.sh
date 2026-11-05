#!/usr/bin/env bash
# Publish the static, read-only SHOWCASE to GitHub Pages (https://eulogep.github.io/Traider-pro/).
# Builds with base path /Traider-pro/, checks it (no API, every page), then pushes ONLY dist/spa to the
# `gh-pages` branch through a temporary worktree. Your working tree and other branches are never touched.
#
#   pnpm deploy:pages          (regenerate the data first with `pnpm showcase:data` if the engine changed)
set -euo pipefail
cd "$(dirname "$0")/.."
REMOTE="${REMOTE:-origin}"

pnpm run build:pages
node e2e/showcase-smoke.mjs --base /Traider-pro/

WT="$(mktemp -d)"
trap 'git worktree remove --force "$WT" >/dev/null 2>&1 || true; rm -rf "$WT"' EXIT
if git ls-remote --exit-code --heads "$REMOTE" gh-pages >/dev/null 2>&1; then
  git fetch -q "$REMOTE" gh-pages
  git worktree add -q -B gh-pages "$WT" "$REMOTE/gh-pages"
else
  git worktree add -q --detach "$WT"
  git -C "$WT" checkout -q --orphan gh-pages
fi
git -C "$WT" rm -rfq --ignore-unmatch . >/dev/null
cp -R dist/spa/. "$WT"/
SRC="$(git rev-parse --short HEAD)"
git -C "$WT" add -A
if git -C "$WT" diff --cached --quiet; then
  echo "Vitrine déjà à jour (aucun changement)."
  exit 0
fi
git -C "$WT" commit -q -m "Vitrine statique (lecture seule) depuis ${SRC}"
git -C "$WT" push -q "$REMOTE" gh-pages
echo "Publié : https://eulogep.github.io/Traider-pro/ (source ${SRC})"
