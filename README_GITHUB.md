# GitHub workflow for this fork

This repository is a fork of:

```text
https://github.com/SamDFr/QCT_POSCAR_generation
```

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

## Daily workflow

### 1. Before starting new work

Synchronize your local branch with the original repository:

```bash
./scripts/sync_with_upstream.sh
```

This fetches the latest `upstream/master`, rebases your local `master` on top of it, and pushes the synchronized result to your fork.

The script refuses to run if you have uncommitted local changes.

### 2. Modify notebooks, README files, or scripts

Work normally in Jupyter, VS Code, or the terminal.

Generated data should stay out of Git:

- `inputs/`
- `model/`
- generated `outputs/`
- POSCAR batches
- trajectories

These paths are ignored through `.gitignore`.

### 3. Review what changed

```bash
git status --short
git diff --stat
```

For notebooks, it is normal that the diff is harder to read. Keep generated output cells small or cleared when possible.

### 4. Commit and push to your fork

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

## If the original repository changes later

Run:

```bash
./scripts/sync_with_upstream.sh
```

If there are conflicts, Git will stop and show the conflicting files. Resolve them, then continue with:

```bash
git add <resolved-files>
git rebase --continue
git push
```

If you are unsure, stop and inspect:

```bash
git status
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

