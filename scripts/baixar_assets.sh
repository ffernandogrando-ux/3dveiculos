#!/usr/bin/env bash
# Baixa (ou completa) a biblioteca de material livre CC0 do canal em assets/. Idempotente: o que já existe é pulado.
#   bash scripts/baixar_assets.sh              # tudo (~200 MB)
#   bash scripts/baixar_assets.sh hdri         # só uma parte: hdri | texturas | modelos | sons | fontes
#   GRANDES=1 bash scripts/baixar_assets.sh    # inclui o Downtown City MegaKit do Quaternius (+223 MB)
# Depois: assets/LICENCAS.md (licença de cada item) e motor3d/biblioteca.py (catalogo(), hdri(), textura_pbr()...).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -I scripts/baixar_assets.py "$@"
