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

# ---------------------------------------------------------------- Quaternius no itch.io ("name your own price", 0)
# Os que os testes usam. O _itch_baixar.py faz o mesmo que o botão "No thanks, just take me to the downloads".
itch() {  # url  pasta  filtro
  mkdir -p "$P/$2"
  "$PY" -I "$RAIZ/scripts/_itch_baixar.py" "$1" "$P/$2" "$3"
  (cd "$P/$2" && for z in *.zip; do unzip -oq "$z"; done)
}
itch https://quaternius.itch.io/universal-animation-library   quaternius_ual  'Standard'
itch https://quaternius.itch.io/universal-animation-library-2 quaternius_ual2 'Standard'
itch https://quaternius.itch.io/universal-base-characters     quaternius_ubc  'Standard'

# ---------------------------------------------------------------- Quaternius (Google Drive, links das páginas do site)
# Em 12/11/2026 o Drive respondeu "Quota exceeded" a TODOS os arquivos destas pastas (limite de download por IP
# dos arquivos públicos muito baixados). Rode de novo mais tarde; o que já baixou é pulado.
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
    "$GDOWN" -q --no-cookies "$url" -O "$out" 2>/dev/null || { rm -f "$out"; echo "falhou (Drive): $caminho"; }
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

# ---------------------------------------------------------------- CMU Graphics Lab Motion Capture Database (ASF/AMC)
# mocap.cs.cmu.edu, direto da fonte; convertido para BVH (24 qps, metros, Y para cima) por motor3d/animacao_pronta.py.
# 141 e 143 foram capturados a 60 qps (a página diz 120, mas a cadência do passo só fica humana a 60).
cmu() {  # sujeito tomadas...
  local s="$1"; shift
  mkdir -p "$M/cmu_amc"
  [ -s "$M/cmu_amc/$s.asf" ] || curl -sSf -m 120 -o "$M/cmu_amc/$s.asf" "http://mocap.cs.cmu.edu/subjects/$s/$s.asf"
  for t in "$@"; do
    [ -s "$M/cmu_amc/${s}_$t.amc" ] || curl -sSf -m 300 -o "$M/cmu_amc/${s}_$t.amc" "http://mocap.cs.cmu.edu/subjects/$s/${s}_$t.amc"
  done
}
cmu 141 14 16 19 20 21 25     # chute+soco, aceno, andar, esperando, dar de ombros, andar
cmu 143 24 25                 # chutes, acenar
cmu 13 27 29                  # apontar/orientar o trânsito, agachamentos
(cd "$RAIZ/motor3d" && "$PY" -c "
import animacao_pronta as ap, glob, os
A, B = '$M/cmu_amc', '$M/cmu_bvh'
for amc in sorted(glob.glob(A + '/*.amc')):
    n = os.path.basename(amc)[:-4]; s = n.split('_')[0]
    ap.asf_amc_para_bvh(f'{A}/{s}.asf', amc, f'{B}/{n}.bvh', fps=24, fps_fonte=60 if s in ('141', '143') else 120)
    print('BVH', n)
")
echo "pronto: $P e $M"
