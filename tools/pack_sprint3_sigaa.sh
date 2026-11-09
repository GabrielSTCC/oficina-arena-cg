#!/usr/bin/env bash
# Gera ZIP(s) para entrega Sprint 3 no SIGAA.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT}/dist"
FULL_NAME="oficina-arena-sprint3"
LIGHT_NAME="oficina-arena-sprint3-codigo-docs"
THRESHOLD_MB=95

rm -rf "${OUT_DIR}/${FULL_NAME}" "${OUT_DIR}/${LIGHT_NAME}"
mkdir -p "${OUT_DIR}/${FULL_NAME}" "${OUT_DIR}/${LIGHT_NAME}"

copy_tree() {
  local dest="$1"
  local skip_assets="${2:-0}"
  (
    cd "$ROOT"
    find . -mindepth 1 \( \
      -path './.venv' -o -path './.venv/*' -o \
      -path './.git' -o -path './.git/*' -o \
      -path './.cursor' -o -path './.cursor/*' -o \
      -path './dist' -o -path './dist/*' -o \
      -path './docs/_gen_pdfs_equipe.py' -o \
      -path './tools/pack_sprint3_sigaa.sh' -o \
      -name '__pycache__' -o -name '*.pyc' \
    \) -prune -o -print
  ) | while IFS= read -r rel; do
    rel="${rel#./}"
    [[ -z "$rel" ]] && continue
    if [[ "$skip_assets" == "1" && ( "$rel" == assets || "$rel" == assets/* ) ]]; then
      continue
    fi
    src="${ROOT}/${rel}"
    dst="${dest}/${rel}"
    if [[ -d "$src" ]]; then
      mkdir -p "$dst"
    else
      mkdir -p "$(dirname "$dst")"
      cp -a "$src" "$dst"
    fi
  done
}

copy_tree "${OUT_DIR}/${FULL_NAME}" 0
copy_tree "${OUT_DIR}/${LIGHT_NAME}" 1
mkdir -p "${OUT_DIR}/${LIGHT_NAME}/assets"
printf '%s\n' \
  "Assets (NPZ, glTF, texturas, audio) nao incluidos neste ZIP." \
  "Baixe o repositorio completo:" \
  "https://github.com/GabrielSTCC/oficina-arena-cg" \
  > "${OUT_DIR}/${LIGHT_NAME}/assets/LEIA-ME_ASSETS.txt"

cd "${OUT_DIR}"
rm -f "${FULL_NAME}.zip" "${LIGHT_NAME}.zip"
zip -qr "${FULL_NAME}.zip" "${FULL_NAME}"
zip -qr "${LIGHT_NAME}.zip" "${LIGHT_NAME}"

FULL_MB=$(du -m "${FULL_NAME}.zip" | awk '{print $1}')
LIGHT_MB=$(du -m "${LIGHT_NAME}.zip" | awk '{print $1}')
echo "FULL  ${FULL_NAME}.zip  (${FULL_MB} MiB)"
echo "LIGHT ${LIGHT_NAME}.zip (${LIGHT_MB} MiB)"
if (( FULL_MB > THRESHOLD_MB )); then
  echo "AVISO: ZIP completo > ${THRESHOLD_MB} MiB — use o LIGHT no SIGAA + link GitHub."
  echo "RECOMENDADO: ${OUT_DIR}/${LIGHT_NAME}.zip"
else
  echo "RECOMENDADO: ${OUT_DIR}/${FULL_NAME}.zip"
fi
ls -lh "${FULL_NAME}.zip" "${LIGHT_NAME}.zip"
