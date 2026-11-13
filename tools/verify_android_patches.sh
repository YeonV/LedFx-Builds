#!/usr/bin/env bash
# Replays the exact patch-apply sequence BuildAndroidMatrix.yml uses, against
# a genuinely fresh clone of LedFx/LedFx@main - not a claim that a patch was
# checked, a reproducible check anyone can run and get the same answer from.
#
# Incident this exists because of (2026-08-15): boot_status.patch was called
# "verified" twice without this existing - once checked against a stale
# local mirror (_pipeline_android/deps/ledfx) instead of live upstream, once
# a different change (getForegroundServiceType(), not a patch, see
# android-framework-method-guard.js) not checked against anything at all.
# Both killed a full Android release, each ~20 CI minutes across 6 archs.
#
# Usage: tools/verify_android_patches.sh
# Exits 0 only if every patch below applies cleanly, in order, against a
# fresh clone. Run this yourself - don't take "verified" as someone's word.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_DIR="$REPO_ROOT/tools"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# The order is read from the "apply patches" step in
# .github/workflows/BuildAndroidMatrix.yml, so it cannot drift. Order matters:
# each patch is applied against the PREVIOUS patch's output, not independently
# against bare main - a patch that applies cleanly on its own can still fail
# here if an earlier patch already rewrote the context it anchors on.
mapfile -t PATCHES < <(grep -oE 'git apply [a-z_]+\.patch' "$REPO_ROOT/.github/workflows/BuildAndroidMatrix.yml" | awk '{print $3}' | awk '!seen[$0]++')
[ ${#PATCHES[@]} -gt 0 ] || { echo "no patches found in BuildAndroidMatrix.yml" >&2; exit 1; }

# CI copies every patch by name before applying it; one that is applied but not
# copied fails the build with "can't open patch" although it applies cleanly
# here. Check both workflows for that.
for wf in BuildAndroidMatrix.yml BuildPipelineUV.yml; do
  path="$REPO_ROOT/.github/workflows/$wf"
  for p in $(grep -oE 'git apply [a-z_]+\.patch' "$path" | awk '{print $3}' | sort -u); do
    if ! grep -qE "cp \./src2/tools/$p " "$path"; then
      echo "==> $wf applies $p but never copies it" >&2
      exit 1
    fi
  done
done
echo "==> every applied patch is also copied, in both workflows"

echo "==> Cloning LedFx/LedFx@main (fresh, depth 1) ..."
git clone --depth 1 --quiet https://github.com/LedFx/LedFx.git "$WORK_DIR/ledfx"
echo "    HEAD: $(git -C "$WORK_DIR/ledfx" rev-parse HEAD)"
echo ""

cd "$WORK_DIR/ledfx"
FAILED=0
for patch in "${PATCHES[@]}"; do
  patch_path="$PATCH_DIR/$patch"
  if [ ! -f "$patch_path" ]; then
    echo "==> SKIP $patch (not found at $patch_path)"
    continue
  fi
  echo "==> Applying $patch ..."
  # git apply, exactly as CI runs it: `patch` matches context more leniently
  # and has reported patches clean that CI then rejected.
  if git apply "$patch_path"; then
    echo "    OK: $patch"
  else
    echo "    FAILED: $patch"
    FAILED=1
  fi
  echo ""
done

if [ "$FAILED" -eq 0 ]; then
  echo "ALL PATCHES APPLIED CLEANLY against fresh LedFx/LedFx@main, in CI order."
  exit 0
else
  echo "AT LEAST ONE PATCH FAILED. Do not call these patches verified or ready."
  exit 1
fi
