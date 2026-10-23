#!/usr/bin/env bash
# Adiciona a pasta da submissão ao git respeitando o .gitignore dela.
# Necessário porque o .gitignore da raiz do repositório ignora submissions/ e `git add -f`
# ignora também os .gitignore internos.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
sub="submissions/tiago-canatelli"
cd "$root"
git add -f "$sub"
git ls-files -ci --exclude-from="$sub/.gitignore" -- "$sub" | while IFS= read -r f; do
  git rm --cached -q -- "$f"
done
git status --short -- "$sub"
