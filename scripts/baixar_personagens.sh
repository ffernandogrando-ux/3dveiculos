#!/usr/bin/env bash
# Baixa de novo os personagens animados (Quaternius, CC0) e as capturas de movimento (CMU) usados pelos testes de
# motor3d/animacao_pronta.py. Tudo cai em assets/ (fora do git). Origem e licença: assets/LICENCAS_personagens.md.
#   bash scripts/baixar_personagens.sh
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-$HOME/.venv-video/bin/python}"
"$PY" -m pip install -q gdown
GDOWN="$(dirname "$PY")/gdown"
P="$RAIZ/assets/personagens"
M="$RAIZ/assets/mocap"
mkdir -p "$P" "$M"

# ---------------------------------------------------------------- Quaternius (Google Drive, links das páginas do site)
# pasta_do_drive  destino  filtro (regex nos caminhos da pasta)
baixa_drive() {
  local id="$1" dest="$2" filtro="$3"
  mkdir -p "$P/$dest"
  "$GDOWN" --json --no-cookies "https://drive.google.com/drive/folders/$id" > "$P/$dest/_lista.json"
  "$PY" - "$P/$dest/_lista.json" "$filtro" <<'EOF' | while IFS=$'\t' read -r url caminho; do
import json, re, sys
for e in json.load(open(sys.argv[1])):
    if re.search(sys.argv[2], e["path"]):
        print(e["url"] + "\t" + e["path"])
EOF
    out="$P/$dest/$caminho"
    [ -s "$out" ] && continue
    mkdir -p "$(dirname "$out")"
    "$GDOWN" -q --no-cookies "$url" -O "$out" || echo "falhou: $caminho"
  done
}
# Ultimate Animated Character Pack (quaternius.com/packs/ultimatedanimatedcharacter.html)
baixa_drive 1sNi1AfenfPRrvRt5yfaj5QMMd6KKcUJ5 quaternius_ultimate_animated \
  '^(License\.txt|Preview\.png|FBX/(Worker_Male|Casual_Male|Casual2_Male|Casual3_Male|Casual_Bald|Worker_Female)\.fbx)$'
# Ultimate Modular Men (quaternius.com/packs/ultimatemodularcharacters.html) — versão "Humanoid Rig" (ossos padrão)
baixa_drive 1USAAquX2JJWuA2m6zol0KUkFe3UkZ8zX quaternius_modular_men \
  '^(License\.txt|How To Use\.txt|Preview\.jpg|Humanoid Rig/Individual Characters/FBX/(Worker|Casual|Casual2|Farmer)\.fbx|Individual Characters/FBX/(Worker|Casual_2|Casual_Hoodie)\.fbx)$'
# Animated Men Pack (quaternius.com/packs/animatedmen.html)
baixa_drive 17LibivOaUidsQhSkcxP3YYvDr0n7wIwu quaternius_animated_men \
  '^(License\.txt|Preview\.jpg|FBX/(Smooth_Male_Casual|Smooth_Male_Shirt|Male_Casual)\.fbx)$'

