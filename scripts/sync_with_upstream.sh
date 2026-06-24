#!/usr/bin/env bash
set -euo pipefail

apply_changes="false"
if [[ "${1:-}" == "--apply" ]]; then
  apply_changes="true"
elif [[ -n "${1:-}" ]]; then
  echo "Usage: ./scripts/sync_with_upstream.sh [--apply]"
  echo
  echo "Without --apply: fetch upstream and show what would change."
  echo "With --apply: create a backup branch, rebase on upstream/master, and push."
  exit 1
fi

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

read -r origin_ahead local_ahead_origin < <(git rev-list --left-right --count origin/master...HEAD)
read -r upstream_ahead local_ahead_upstream < <(git rev-list --left-right --count upstream/master...HEAD)

echo
echo "Current divergence:"
echo "  origin commits not in local:    ${origin_ahead}"
echo "  local commits not in origin:    ${local_ahead_origin}"
echo "  upstream commits not in local:  ${upstream_ahead}"
echo "  local commits not in upstream:  ${local_ahead_upstream}"

echo
if [[ "${upstream_ahead}" == "0" ]]; then
  echo "No new upstream commits need to be integrated."
  echo "Your fork currently contains ${local_ahead_upstream} commit(s) not present upstream."
else
  merge_base="$(git merge-base HEAD upstream/master)"
  echo "Files changed by upstream commits not yet integrated locally:"
  git diff --name-status "${merge_base}"..upstream/master || true
fi

echo
if [[ "${apply_changes}" != "true" ]]; then
  echo "Dry run only. No rebase was performed."
  echo
  echo "If you really want to integrate upstream changes, run:"
  echo "  ./scripts/sync_with_upstream.sh --apply"
  echo
  echo "This is intentionally conservative because this fork contains substantial customizations."
  exit 0
fi

if [[ "${upstream_ahead}" == "0" ]]; then
  echo "Nothing to apply from upstream. Exiting without rebase."
  exit 0
fi

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_branch="backup/master-before-upstream-sync-${timestamp}"

echo "Creating backup branch: ${backup_branch}"
git branch "${backup_branch}"
git push origin "${backup_branch}"

echo "Rebasing local master on upstream/master..."
git rebase upstream/master

echo "Pushing synchronized master to your fork..."
git push -u origin master

echo "Done. Your local repository and fork are synchronized."
echo "Backup branch kept at origin/${backup_branch}."
