#!/usr/bin/env bash
# Runs the patch steps of the CI workflows exactly as GitHub runs them, against
# a fresh clone of LedFx/LedFx@main:
#
#   BuildPipelineUV.yml     job build                (desktop chain)
#   BuildAndroidMatrix.yml  jobs build_archs and build_archs_release
#
# The step's own `run:` text is extracted from the workflow and executed with
# `bash -e` in the same layout CI uses (this repo at ./src2, the core checkout
# at the step's path), so copy lines, apply order and error handling are the
# real ones. A local replay of "the same" commands has twice reported a chain
# as fine that CI then rejected (patch fuzz, a patch applied but never copied);
# this runs the step itself instead.
#
#   tools/verify_android_patches.sh
#
# Needs git, bash and python3 with PyYAML (or uv to fetch it).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

if python3 -c "import yaml" 2>/dev/null; then
  PY=(python3)
else
  PY=(uv run -q --no-project --with pyyaml python)
fi

# workflow  job  core-checkout-path
STEPS=(
  "BuildPipelineUV.yml build src"
  "BuildAndroidMatrix.yml build_archs deps/ledfx"
  "BuildAndroidMatrix.yml build_archs_release deps/ledfx"
)

echo "==> Cloning LedFx/LedFx@main (fresh, depth 1) ..."
git clone --depth 1 --quiet https://github.com/LedFx/LedFx.git "$WORK_DIR/core"
echo "    HEAD: $(git -C "$WORK_DIR/core" rev-parse HEAD)"

FAILED=0
for entry in "${STEPS[@]}"; do
  read -r workflow job core_path <<<"$entry"
  label="$workflow / $job"
  run_dir="$WORK_DIR/run_${job}"
  mkdir -p "$run_dir/$(dirname "$core_path")"
  ln -s "$REPO_ROOT" "$run_dir/src2"
  git clone --quiet "$WORK_DIR/core" "$run_dir/$core_path"

  # The one step of the job that copies and applies the patches.
  "${PY[@]}" - "$REPO_ROOT/.github/workflows/$workflow" "$job" > "$run_dir/step.sh" <<'PY'
import sys, yaml
workflow, job = sys.argv[1], sys.argv[2]
steps = [s for s in yaml.safe_load(open(workflow))["jobs"][job]["steps"]
         if "git apply" in s.get("run", "") and ".patch" in s.get("run", "")]
if len(steps) != 1:
    sys.exit(f"expected one patch step in {job}, found {len(steps)}")
if "${{" in steps[0]["run"]:
    sys.exit(f"patch step in {job} uses ${{{{ }}}} expressions; cannot run it locally")
print(steps[0]["run"])
PY

  echo ""
  echo "==> $label: running its patch step"
  if (cd "$run_dir" && bash -e step.sh) > "$run_dir/step.log" 2>&1; then
    echo "    OK: $label"
  else
    echo "    FAILED: $label"
    tail -n 15 "$run_dir/step.log" | sed 's/^/      /'
    FAILED=1
  fi
  rejects=$(find "$run_dir/$core_path" -name '*.rej' | wc -l)
  if [ "$rejects" -ne 0 ]; then
    echo "    FAILED: $label left $rejects .rej file(s)"
    FAILED=1
  fi
done

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "ALL CI PATCH STEPS PASSED against fresh LedFx/LedFx@main."
  exit 0
else
  echo "AT LEAST ONE CI PATCH STEP FAILED. Do not call these patches verified or ready."
  exit 1
fi
