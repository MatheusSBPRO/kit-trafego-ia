#!/usr/bin/env bash
# Instala as ferramentas do kit-trafego-ia. Cada ferramenta tem o próprio instalar.sh na pasta dela;
# este aqui só escolhe quais rodar e chama um por um.
#
#   ./instalar.sh --global                    instala todas, para valer em qualquer pasta
#   ./instalar.sh --global nome1 nome2        instala só as escolhidas
#   ./instalar.sh nome1 nome2                 roda o instalador de cada uma no modo local (confere o ambiente)
#   ./instalar.sh --listar                    mostra as ferramentas
#
# A ia-whatsapp-atendimento não tem modo global: ela é um programa que roda no seu computador e o
# instalador dela monta a bridge do WhatsApp dentro da própria pasta.
set -uo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
FERRAMENTAS=(subir-campanha-meta checar-criativo-meta ia-whatsapp-atendimento video-3d-explicativo youtube-especialista)

descricao() {
  case "$1" in
    subir-campanha-meta)     echo "sobe campanha na Meta pela Graph API, tudo pausado" ;;
    checar-criativo-meta)    echo "checa criativo contra a política de publicidade da Meta" ;;
    ia-whatsapp-atendimento) echo "IA que atende no WhatsApp do negócio (começa em modo sombra)" ;;
    video-3d-explicativo)    echo "roteiro vira vídeo vertical 3D com narração e legenda" ;;
    youtube-especialista)    echo "método para montar e operar o YouTube de um especialista" ;;
  esac
}

ajuda() {
  sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
}

listar() {
  echo "Ferramentas do kit:"
  for f in "${FERRAMENTAS[@]}"; do
    printf '  %-26s %s\n' "$f" "$(descricao "$f")"
  done
}

existe() {
  local f
  for f in "${FERRAMENTAS[@]}"; do [ "$f" = "$1" ] && return 0; done
  return 1
}

GLOBAL=0
ESCOLHIDAS=()
for arg in "$@"; do
  case "$arg" in
    --global) GLOBAL=1 ;;
    --listar|--list) listar; exit 0 ;;
    -h|--help) ajuda; echo; listar; exit 0 ;;
    -*) echo "Opção desconhecida: $arg" >&2; ajuda >&2; exit 2 ;;
    *)
      if existe "$arg"; then
        ESCOLHIDAS+=("$arg")
      else
        echo "Ferramenta desconhecida: $arg" >&2
        listar >&2
        exit 2
      fi
      ;;
  esac
done

if [ "$GLOBAL" = 0 ] && [ ${#ESCOLHIDAS[@]} -eq 0 ]; then
  ajuda
  echo
  listar
  exit 0
fi
if [ ${#ESCOLHIDAS[@]} -eq 0 ]; then
  ESCOLHIDAS=("${FERRAMENTAS[@]}")
fi

OK=()
FALHOU=()
for f in "${ESCOLHIDAS[@]}"; do
  inst="$RAIZ/ferramentas/$f/instalar.sh"
  echo
  echo "================ $f"
  if [ ! -f "$inst" ]; then
    echo "  sem instalar.sh em ferramentas/$f: veja o README da pasta"
    FALHOU+=("$f")
    continue
  fi
  args=()
  if [ "$GLOBAL" = 1 ]; then
    if [ "$f" = "ia-whatsapp-atendimento" ]; then
      echo "  (esta não tem modo global: monta a bridge dentro de ferramentas/$f)"
    else
      args=(--global)
    fi
  fi
  if (cd "$RAIZ/ferramentas/$f" && bash "$inst" ${args[@]+"${args[@]}"}); then
    OK+=("$f")
  else
    FALHOU+=("$f")
  fi
done

echo
echo "================ resumo"
[ ${#OK[@]} -gt 0 ] && echo "  instaladas: ${OK[*]}"
if [ ${#FALHOU[@]} -gt 0 ]; then
  echo "  com problema: ${FALHOU[*]} (leia a saída acima)"
  exit 1
fi
exit 0
