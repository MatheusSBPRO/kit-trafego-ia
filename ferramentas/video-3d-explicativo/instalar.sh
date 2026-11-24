#!/usr/bin/env bash
# Instala a skill de vídeo 3D explicativo.
#
#   ./instalar.sh            confere o ambiente. A skill já vale quando você roda `claude`
#                            (ou `codex`) dentro desta pasta.
#   ./instalar.sh --global   copia a skill, com os scripts e o modelo, para ~/.claude/skills
#                            e, se existir, para ~/.codex/skills. Vale em qualquer pasta.
#                            Uma skill com o mesmo nome vira backup (.bak-AAAAMMDD) antes de ser trocada.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
SKILL="video-3d-explicativo"
GLOBAL=0
[ "${1:-}" = "--global" ] && GLOBAL=1

ok()    { printf '  \033[32m✓\033[0m %s\n' "$1"; }
aviso() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "Vídeo 3D explicativo · instalação"
echo

echo "1. Ambiente"
if command -v node >/dev/null 2>&1; then
  ok "node $(node -v)"
else
  aviso "node não encontrado. Instale o Node 18+ (nodejs.org)."
fi
if command -v python3 >/dev/null 2>&1; then
  ok "python3 $(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
  python3 -c 'import numpy' >/dev/null 2>&1 && ok "numpy" || aviso "numpy não encontrado: pip install numpy"
else
  aviso "python3 não encontrado. Instale o Python 3.9+ (python.org)."
fi
command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg" || aviso "ffmpeg não encontrado: brew install ffmpeg (Mac) ou apt install ffmpeg (Linux)."
if python3 -c 'import mlx_whisper' >/dev/null 2>&1; then
  ok "whisper (mlx-whisper)"
elif python3 -c 'import faster_whisper' >/dev/null 2>&1; then
  ok "whisper (faster-whisper)"
elif python3 -c 'import whisper' >/dev/null 2>&1; then
  ok "whisper (openai-whisper)"
else
  aviso "whisper não encontrado: pip install mlx-whisper (Mac M1+), faster-whisper ou openai-whisper."
fi
if [ -n "${FISH_API_KEY:-}" ]; then
  ok "FISH_API_KEY no ambiente"
elif [ -n "${ELEVENLABS_API_KEY:-}" ]; then
  ok "ELEVENLABS_API_KEY no ambiente"
else
  aviso "sem chave de voz: exporte FISH_API_KEY (fish.audio > API Keys) ou ELEVENLABS_API_KEY."
fi
FONTE=0
for f in "$HOME/Library/Fonts/Montserrat-Bold.ttf" /Library/Fonts/Montserrat-Bold.ttf /usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf "$HOME/.fonts/Montserrat-Bold.ttf"; do
  [ -f "$f" ] && FONTE=1 && break
done
[ "$FONTE" = 1 ] && ok "fonte Montserrat Bold (marca d'água)" || aviso "fonte Montserrat Bold não instalada: o vídeo sai sem marca d'água."
command -v claude >/dev/null 2>&1 && ok "Claude Code instalado"
command -v codex  >/dev/null 2>&1 && ok "Codex instalado"

chmod +x "$RAIZ"/scripts/*.sh "$RAIZ"/scripts/*.py 2>/dev/null || true

copiar_skill() {
  local base="$1" destino="$1/$SKILL" hoje
  hoje="$(date +%Y%m%d)"
  mkdir -p "$base"
  if [ -e "$destino" ]; then
    rm -rf "$destino.bak-$hoje"
    mv "$destino" "$destino.bak-$hoje"
  fi
  mkdir -p "$destino"
  cp "$RAIZ/.claude/skills/$SKILL/SKILL.md" "$destino/"
  cp -R "$RAIZ/scripts" "$destino/"
  mkdir -p "$destino/modelo"
  (cd "$RAIZ/modelo" && cp alinhar.py cena.html mix.py package.json render.js roteiro.txt wm.txt "$destino/modelo/")
  ok "skill copiada para $destino"
}

if [ "$GLOBAL" = 1 ]; then
  echo
  echo "2. Instalação global"
  copiar_skill "$HOME/.claude/skills"
  if [ -d "$HOME/.codex" ]; then
    copiar_skill "$HOME/.codex/skills"
  fi
fi

echo
echo "Pronto. Abra o Claude Code ou o Codex e peça:"
echo "  \"faz um vídeo 3D explicando <tema>, com a voz <ID do fish.audio>\""
