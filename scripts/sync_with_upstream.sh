#!/usr/bin/env bash
set -euo pipefail

branch="$(git branch --show-current)"
if [[ "${branch}" != "master" ]]; then
  echo "This script expects branch 'master', but you are on '${branch}'."
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Your working tree has uncommitted changes."
  echo "Commit, stash, or discard them before syncing with upstream."
  git status --short
  exit 1
fi

origin_url="$(git remote get-url origin)"
upstream_url="$(git remote get-url upstream)"

if [[ "${origin_url}" != *"arivero3122/QCT_POSCAR_generation"* ]]; then
  echo "Unexpected origin remote: ${origin_url}"
  echo "Expected your fork under arivero3122."
  exit 1
fi

if [[ "${upstream_url}" != *"SamDFr/QCT_POSCAR_generation"* ]]; then
  echo "Unexpected upstream remote: ${upstream_url}"
  echo "Expected the original SamDFr repository."
  exit 1
fi

echo "Fetching origin and upstream..."
git fetch origin master
git fetch upstream master

echo "Rebasing local master on upstream/master..."
git rebase upstream/master

echo "Pushing synchronized master to your fork..."
git push -u origin master

echo "Done. Your local repository and fork are synchronized."

