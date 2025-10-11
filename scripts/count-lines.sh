#!/usr/bin/env bash
set -euo pipefail

projects=(commonUI expertAgent graphAiServer jobqueue myscheduler myVault)
test_dir_candidates=(tests __tests__ test spec)
test_exclude_list="$(IFS=,; echo "${test_dir_candidates[*]}")"
prod_exclude_list=".venv,node_modules,${test_exclude_list}"

if ! command -v cloc >/dev/null 2>&1; then
  echo "clocが見つかりません。brew install cloc を実行してください。" >&2
  exit 1
fi

for project in "${projects[@]}"; do
  echo "=== ${project} ==="
  echo "-- プロダクションコード --"
  cloc --exclude-dir="${prod_exclude_list}" "${project}"

  test_targets=()
  while IFS= read -r -d '' dir; do
    test_targets+=("$dir")
  done < <(find "${project}" -type d \( -name "tests" -o -name "__tests__" -o -name "test" -o -name "spec" \) -print0)

  if [ ${#test_targets[@]} -eq 0 ]; then
    echo "-- テストコード --"
    echo "テストディレクトリが見つかりません。"
  else
    echo "-- テストコード --"
    cloc --exclude-dir=.venv,node_modules "${test_targets[@]}"
  fi
  echo
done
