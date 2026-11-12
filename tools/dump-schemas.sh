#!/usr/bin/env bash
# Dump the config schemas of upstream LedFx main with this repo's patches applied,
# the input for the frontend's generated config types (yarn generate:types).
#
#   tools/dump-schemas.sh [out.json] [frontend-dir]
#
# out.json      where to write the dump (default: ledfx-schemas.json)
# frontend-dir  if given, also regenerate <frontend-dir>/src/api/ledfx.config.types.ts
#
# The tree is the desktop chain exactly as BuildPipelineUV.yml applies it (the order
# is read from that workflow, so it cannot drift), plus the schema part of the
# Android-only remote_submix_echo.patch: the frontend serves both builds. That
# patch's api/utils.py hunk collides with stems.patch and is irrelevant to schemas.
# Needs git, uv (>= 0.12.12, or uvx to fetch one) and, for frontend-dir, node.
set -euo pipefail

TOOLS=$(cd "$(dirname "$0")" && pwd)
WORKFLOW="$TOOLS/../.github/workflows/BuildPipelineUV.yml"
OUT=$(realpath -m "${1:-ledfx-schemas.json}")
FRONTEND=${2:+$(realpath "$2")}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

mapfile -t PATCHES < <(grep -oE 'git apply [a-z_]+\.patch' "$WORKFLOW" | awk '{print $3}')
[ ${#PATCHES[@]} -gt 0 ] || { echo "no patches found in $WORKFLOW" >&2; exit 1; }

git clone -q --depth 1 https://github.com/LedFx/LedFx.git "$WORK/ledfx"
cd "$WORK/ledfx"
echo "LedFx main $(git rev-parse --short HEAD)"
for patch in "${PATCHES[@]}"; do
  git apply "$TOOLS/$patch"
done
git apply --include=ledfx/configuration/models.py "$TOOLS/remote_submix_echo.patch"
echo "applied ${PATCHES[*]} + remote_submix_echo (schema part)"

if uv --version 2>/dev/null | awk '{split($2, v, "."); exit !(v[1] > 0 || v[2] >= 12)}'; then
  UV=(uv)
else
  UV=(uvx --from 'uv>=0.12.12' uv)
fi
# A throw-away config dir: a core run must never touch the real config.json.
"${UV[@]}" run -q python -m ledfx --dump-schemas "$OUT" -c "$WORK/config" >/dev/null
echo "wrote $OUT"

if [ -n "$FRONTEND" ]; then
  (cd "$FRONTEND" && node scripts/generate-config-types.mjs "$OUT")
fi
