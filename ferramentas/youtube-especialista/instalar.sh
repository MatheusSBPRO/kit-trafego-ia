#!/usr/bin/env bash
# Instala a skill youtube-especialista (método, referências e templates).
#
#   ./instalar.sh            confere o ambiente. A skill já vale quando você roda `claude`
#                            (ou `codex`) dentro desta pasta.
#   ./instalar.sh --global   copia a skill para ~/.claude/skills e, se existir, para ~/.codex/skills.
#                            O que for trocado vira backup (.bak-AAAAMMDD). Uma pasta scripts/ que você
#                            já tenha lá, com config.json e login, fica como está.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
SKILL="youtube-especialista"
GLOBAL=0
[ "${1:-}" = "--global" ] && GLOBAL=1
ITENS=(SKILL.md README.md references metodo templates)

ok()    { printf '  \033[32m✓\033[0m %s\n' "$1"; }
aviso() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "YouTube do especialista · instalação"
echo

echo "1. Ambiente"
command -v claude >/dev/null 2>&1 && ok "Claude Code instalado"
command -v codex  >/dev/null 2>&1 && ok "Codex instalado"
command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg" || aviso "ffmpeg não encontrado (corte, reenquadre e render do vídeo)."
command -v yt-dlp >/dev/null 2>&1 && ok "yt-dlp" || aviso "yt-dlp não encontrado (baixar vídeo e comentário público do próprio canal para análise)."
aviso "os scripts de automação do Studio (pasta scripts/) não fazem parte deste repositório:"
aviso "a skill funciona com o método, as referências e os templates."

copiar_skill() {
  local destino="$1/$SKILL" hoje item
  hoje="$(date +%Y%m%d)"
  mkdir -p "$destino"
  if [ -f "$destino/SKILL.md" ]; then
    rm -rf "$destino.bak-$hoje"
    mkdir -p "$destino.bak-$hoje"
    for item in "${ITENS[@]}"; do
      [ -e "$destino/$item" ] && cp -R "$destino/$item" "$destino.bak-$hoje/"
    done
    ok "versão anterior guardada em $destino.bak-$hoje"
  fi
  for item in "${ITENS[@]}"; do
    rm -rf "${destino:?}/$item"
    cp -R "$RAIZ/$item" "$destino/"
  done
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
echo "  \"usa a skill youtube-especialista e faz o diagnóstico do canal do meu expert\""
