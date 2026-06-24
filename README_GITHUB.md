# GitHub workflow for this fork

This repository is a fork of:

```text
https://github.com/SamDFr/QCT_POSCAR_generation
```

The original project and its earlier commit history are credited to **Samuel Del Fre**. This fork keeps that history intact and adds Alejandro Rivero's local workflow customizations on top.

Your fork is:

```text
https://github.com/arivero3122/QCT_POSCAR_generation
```

The recommended convention is:

- `origin`: your fork, where your commits are pushed.
- `upstream`: the original student repository, used only to fetch future updates.

Check this at any time with:

```bash
git remote -v
```

Expected output:

```text
origin    https://github.com/arivero3122/QCT_POSCAR_generation.git
upstream  https://github.com/SamDFr/QCT_POSCAR_generation.git
```

## Recommended workflow for a heavily customized fork

This fork contains substantial local customization. Do not automatically merge every upstream change unless you have reviewed what changed.

The safest routine is:

1. Commit your own work to your fork.
2. Inspect upstream changes without applying them.
3. Integrate upstream only when the changes are useful.
4. Keep a backup branch before any rebase.

### 1. Before starting new work

```bash
git status --short
```

If there are changes, commit them first:

```bash
./scripts/publish_update.sh "Describe your update"
```

### 2. Inspect upstream changes

Run:

```bash
./scripts/sync_with_upstream.sh
```

By default this is a dry run. It fetches `origin` and `upstream`, then shows what files changed upstream. It does **not** rebase, merge, or push.

This conservative default is intentional because your version may diverge significantly from the original project.

### 3. Apply upstream changes only if you want them

If the dry run looks safe, run:

```bash
./scripts/sync_with_upstream.sh --apply
```

This will:

1. Refuse to run if your working tree is dirty.
2. Fetch `origin/master` and `upstream/master`.
3. Create a backup branch named like `backup/master-before-upstream-sync-YYYYMMDD-HHMMSS`.
4. Push that backup branch to your fork.
5. Rebase your `master` on top of `upstream/master`.
6. Push the rebased `master` to your fork.

If conflicts happen, Git stops and your backup branch is already saved.

### 4. Modify notebooks, README files, or scripts

Work normally in Jupyter, VS Code, or the terminal.

Generated data should stay out of Git:

- `inputs/`
- `model/`
- generated `outputs/`
- POSCAR batches
- trajectories

These paths are ignored through `.gitignore`.

### 5. Review what changed

```bash
git status --short
git diff --stat
```

For notebooks, it is normal that the diff is harder to read. Keep generated output cells small or cleared when possible.

### 6. Commit and push to your fork

Use the helper script:

```bash
./scripts/publish_update.sh "Short commit message"
```

Example:

```bash
./scripts/publish_update.sh "Update QCT POSCAR output organization"
```

The script will:

1. Check that you are on `master`.
2. Check that your fork remote is reachable.
3. Stop if your local branch is behind `origin/master`.
4. Stage all non-ignored changes.
5. Show the staged files and diff summary.
6. Ask for confirmation.
7. Commit with your configured Git identity.
8. Push to your fork.

## If upstream conflicts with your customization

If `./scripts/sync_with_upstream.sh --apply` reports conflicts, do not panic. Your pre-sync state is saved in a backup branch on your fork.

First inspect:

```bash
git status
```

If you want to abandon the integration:

```bash
git rebase --abort
```

If you want to resolve the conflicts, edit the conflicting files, then continue:

```bash
git add <resolved-files>
git rebase --continue
git push
```

If the result is bad after finishing the rebase, recover from the backup branch. List backups with:

```bash
git branch -a | grep backup/master-before-upstream-sync
```

Then reset to one backup only if you are sure:

```bash
git reset --hard origin/backup/master-before-upstream-sync-YYYYMMDD-HHMMSS
git push --force-with-lease origin master
```

## Authorship

Do not rewrite old commits from the original repository. The previous commits should keep the original author.

Your new commits should use:

```text
Alejandro Rivero <arivero3122@gmail.com>
```

Check the current local identity with:

```bash
git config user.name
git config user.email
```

Set it for this repository with:

```bash
git config user.name "Alejandro Rivero"
git config user.email "arivero3122@gmail.com"
```
