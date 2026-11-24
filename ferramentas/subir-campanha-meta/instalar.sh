#!/usr/bin/env bash
# Instala o agente e a skill de subir campanha na Meta.
#
#   ./instalar.sh            confere o ambiente (python3, token, Claude Code ou Codex). Não copia nada.
#   ./instalar.sh --global   copia o agente para ~/.claude/agents e a skill para ~/.claude/skills
#                            (e a skill para ~/.codex/skills, se existir). O .env e o clientes.json que
#                            já estiverem lá são mantidos; o que for trocado vira backup (.bak-AAAAMMDD).
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
SKILL="subidor-campanha"
GLOBAL=0
[ "${1:-}" = "--global" ] && GLOBAL=1

ok()    { printf '  \033[32m✓\033[0m %s\n' "$1"; }
aviso() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "Subir campanha na Meta · instalação"
echo

echo "1. Ambiente"
if command -v python3 >/dev/null 2>&1; then
  ok "python3 $(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
  python3 -m py_compile "$RAIZ/skills/$SKILL/scripts/meta_subir.py" && ok "meta_subir.py compila"
else
  aviso "python3 não encontrado. Instale o Python 3.9+ (python.org)."
fi
if [ -n "${META_TOKEN:-}" ]; then
  ok "META_TOKEN no ambiente"
else
  aviso "sem META_TOKEN no ambiente: cole o token no .env da skill depois de instalar (veja o README)."
fi
command -v claude >/dev/null 2>&1 && ok "Claude Code instalado"
command -v codex  >/dev/null 2>&1 && ok "Codex instalado"

copiar_skill() {
  local destino="$1/$SKILL" hoje item
  hoje="$(date +%Y%m%d)"
  mkdir -p "$destino"
  if [ -f "$destino/SKILL.md" ]; then
    rm -rf "$destino.bak-$hoje"
    mkdir -p "$destino.bak-$hoje"
    for item in SKILL.md references scripts clientes.exemplo.json; do
      [ -e "$destino/$item" ] && cp -R "$destino/$item" "$destino.bak-$hoje/"
    done
    ok "versão anterior guardada em $destino.bak-$hoje (sem .env e sem clientes.json)"
  fi
  cp -R "$RAIZ/skills/$SKILL/." "$destino/"
  if [ ! -f "$destino/.env" ]; then
    cp "$RAIZ/.env.exemplo" "$destino/.env"
    chmod 600 "$destino/.env"
    aviso "cole o token em $destino/.env"
  fi
  if [ ! -f "$destino/clientes.json" ]; then
    cp "$destino/clientes.exemplo.json" "$destino/clientes.json"
    aviso "cadastre suas contas em $destino/clientes.json"
  fi
  ok "skill copiada para $destino"
}

if [ "$GLOBAL" = 1 ]; then
  echo
  echo "2. Instalação global"
  mkdir -p "$HOME/.claude/agents"
  agente="$HOME/.claude/agents/$SKILL.md"
  if [ -f "$agente" ] && ! cmp -s "$agente" "$RAIZ/agents/$SKILL.md"; then
    cp "$agente" "$agente.bak-$(date +%Y%m%d)"
  fi
  cp "$RAIZ/agents/$SKILL.md" "$agente"
  ok "agente copiado para $agente"
  copiar_skill "$HOME/.claude/skills"
  if [ -d "$HOME/.codex" ]; then
    copiar_skill "$HOME/.codex/skills"
  fi
fi

echo
echo "Teste sem tocar na Meta:"
echo "  cd ~/.claude/skills/$SKILL/scripts && cp plano.exemplo.json plano.json"
echo "  python3 meta_subir.py estrutura plano.json --simular"
echo
echo "Pronto. Abra o Claude Code e peça:"
echo "  \"sobe a campanha de teste do cliente X: <oferta>, criativos em <pasta>, página <link>\""
