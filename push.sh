#!/usr/bin/env bash
set -e
REPO="https://github.com/techwithblemac/blemac-shell.git"
command -v git >/dev/null || { echo "Git is not installed."; exit 1; }
[ -d .git ] || git init
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO"
git add -A
git status --short
read -r -p "Commit message [Fix Android build: pin Python 3.11 + p4a]: " MESSAGE
MESSAGE=${MESSAGE:-Fix Android build: pin Python 3.11 + p4a}
git commit -m "$MESSAGE"
git push -u origin main --force
echo "Done: https://github.com/techwithblemac/blemac-shell"
