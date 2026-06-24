#!/usr/bin/env bash
set -euo pipefail

commit_message="${1:-}"
if [[ -z "${commit_message}" ]]; then
  echo "Usage: ./scripts/publish_update.sh \"Commit message\""
  exit 1
fi

branch="$(git branch --show-current)"
if [[ "${branch}" != "master" ]]; then
  echo "This script expects branch 'master', but you are on '${branch}'."
  exit 1
fi

origin_url="$(git remote get-url origin)"
if [[ "${origin_url}" != *"arivero3122/QCT_POSCAR_generation"* ]]; then
  echo "Unexpected origin remote: ${origin_url}"
  echo "Expected your fork under arivero3122."
  exit 1
fi

echo "Fetching origin/master..."
git fetch origin master

read -r behind ahead < <(git rev-list --left-right --count origin/master...HEAD)
if [[ "${behind}" != "0" ]]; then
  echo "Your local branch is behind origin/master by ${behind} commit(s)."
  echo "Run './scripts/sync_with_upstream.sh' or 'git pull --rebase origin master' first."
  exit 1
fi

git add -A

if git diff --cached --quiet; then
  echo "No staged changes to commit."
  exit 0
fi

echo
echo "Staged files:"
git status --short

echo
echo "Staged diff summary:"
git diff --cached --stat

echo
read -r -p "Commit and push these changes to origin/master? [y/N] " answer
case "${answer}" in
  y|Y|yes|YES)
    ;;
  *)
    echo "Aborted. Changes remain staged."
    exit 1
    ;;
esac

git commit -m "${commit_message}"
git push -u origin master

echo "Done. Commit pushed to your fork."
