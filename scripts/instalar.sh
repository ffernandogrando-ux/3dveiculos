#!/usr/bin/env bash
# Prepara a máquina para produzir vídeos (idempotente: pode rodar quantas vezes quiser).
# Cria ~/.venv-video com Blender (bpy) e as bibliotecas do motor. Uso:  bash scripts/instalar.sh
set -euo pipefail
VENV="${VENV_VIDEO:-$HOME/.venv-video}"
PY="$VENV/bin/python"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "instalando ffmpeg..."
  (apt-get install -y -q ffmpeg >/dev/null 2>&1 || (apt-get update -q >/dev/null 2>&1 && apt-get install -y -q ffmpeg >/dev/null))
fi

if [ ! -x "$PY" ]; then
  python3 -m venv "$VENV"
fi

if ! "$PY" -c "import bpy, numpy, scipy, PIL, shapely" >/dev/null 2>&1; then
  echo "instalando bpy (Blender) e bibliotecas — leva 1 a 3 minutos..."
  "$PY" -m pip install -q --upgrade pip
  # bpy 5.2 exige Python 3.13; se o pip recusar, a versão do Python da máquina mudou.
  "$PY" -m pip install -q "bpy==5.2.3" numpy scipy pillow shapely
fi

"$PY" -c "import bpy; print('pronto: Blender', bpy.app.version_string, '| python:', '$PY')"
