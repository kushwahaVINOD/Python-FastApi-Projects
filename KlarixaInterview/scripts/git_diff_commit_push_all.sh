#!/usr/bin/env bash
set -eu

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/git_diff_commit_push_all.sh <directory> "<commit message>"

Scans <directory> recursively for Git repositories, prints their uncommitted
diffs, stages all changes, commits them with the provided message, and pushes.

Examples:
  ./scripts/git_diff_commit_push_all.sh . "Update audit log docs"
  ./scripts/git_diff_commit_push_all.sh ~/Desktop/repos "Daily sync"
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ "$#" -lt 2 ]; then
  usage
  exit 1
fi

ROOT_DIR="$1"
shift
COMMIT_MESSAGE="$*"

if [ ! -d "$ROOT_DIR" ]; then
  echo "Directory does not exist: $ROOT_DIR" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is not installed or not available in PATH" >&2
  exit 1
fi

found_repo=false
repo_list="$(mktemp)"
repo_list_sorted="$(mktemp)"
trap 'rm -f "$repo_list" "$repo_list_sorted"' EXIT

if git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT_DIR" rev-parse --show-toplevel >> "$repo_list"
fi

find "$ROOT_DIR" -name .git -print -prune | while IFS= read -r git_path; do
  dirname "$git_path"
done >> "$repo_list"

sort -u "$repo_list" > "$repo_list_sorted"

while IFS= read -r repo_dir; do
  if [ -z "$repo_dir" ]; then
    continue
  fi

  found_repo=true

  echo
  echo "============================================================"
  echo "Repository: $repo_dir"
  echo "============================================================"

  if ! git -C "$repo_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Skipping: not a valid Git work tree"
    continue
  fi

  if [ -z "$(git -C "$repo_dir" status --porcelain --untracked-files=all)" ]; then
    echo "No uncommitted changes. Skipping."
    continue
  fi

  echo
  echo "Status:"
  git -C "$repo_dir" status --short --untracked-files=all

  echo
  echo "Unstaged diff:"
  git -C "$repo_dir" diff --stat
  git -C "$repo_dir" diff

  echo
  echo "Staged diff before adding:"
  git -C "$repo_dir" diff --cached --stat
  git -C "$repo_dir" diff --cached

  echo
  echo "Staging all changes..."
  git -C "$repo_dir" add -A

  echo
  echo "Status after staging:"
  git -C "$repo_dir" status --short --untracked-files=all

  if git -C "$repo_dir" diff --cached --quiet; then
    echo "Nothing staged after git add. Skipping commit."
    echo "Note: Git cannot commit empty folders. Ignored files also remain untracked unless force-added."
    continue
  fi

  echo
  echo "Committing..."
  git -C "$repo_dir" commit -m "$COMMIT_MESSAGE"

  branch="$(git -C "$repo_dir" branch --show-current)"
  if [ -z "$branch" ]; then
    echo "Skipping push: repository is in detached HEAD state."
    continue
  fi

  echo
  echo "Pushing branch: $branch"
  if git -C "$repo_dir" rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
    git -C "$repo_dir" push
  elif git -C "$repo_dir" remote get-url origin >/dev/null 2>&1; then
    git -C "$repo_dir" push -u origin "$branch"
  else
    remote="$(git -C "$repo_dir" remote | head -n 1)"
    if [ -n "$remote" ]; then
      git -C "$repo_dir" push -u "$remote" "$branch"
    else
      echo "Skipping push: no upstream branch and no remote configured."
    fi
  fi
done < "$repo_list_sorted"

if [ "$found_repo" = false ]; then
  echo "No Git repositories found under: $ROOT_DIR"
fi
