#!/usr/bin/env bash
# Pipeline completo: roteiro -> narração -> legenda alinhada -> render 3D -> efeitos -> vídeo final.
#
#   scripts/fazer_video.sh <pasta-do-video> --voz <ID> [--provedor fish|elevenlabs] [--refazer-narracao]
#
# A pasta é uma cópia de modelo/ com o seu roteiro.txt (e a cena ajustada, se o tema mudou).
# Se narracao.wav já existir, ela é reaproveitada, a menos que você passe --refazer-narracao.
# Saídas na pasta: video.mp4 (sem marca), video_final.mp4 (com a marca do wm.txt) e quadros.jpg (6 quadros para conferir).
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
P="${1:?uso: fazer_video.sh <pasta-do-video> --voz <ID> [--provedor fish|elevenlabs] [--refazer-narracao]}"; shift
PROVEDOR=fish; VOZ=""; REFAZER=0
while [ $# -gt 0 ]; do
  case "$1" in
    --voz) VOZ="$2"; shift 2;;
    --provedor) PROVEDOR="$2"; shift 2;;
    --refazer-narracao) REFAZER=1; shift;;
    *) echo "opção desconhecida: $1"; exit 1;;
  esac
done
cd "$P"
dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }

[ -d node_modules/three ] && [ -d node_modules/playwright ] || { echo "· instalando three e playwright"; npm install --silent; npx playwright install chromium >/dev/null; }

if [ ! -f narracao.wav ] || [ "$REFAZER" = 1 ]; then
  [ -n "$VOZ" ] || { echo "Falta --voz <ID> para gerar a narração."; exit 1; }
  echo "1. narração ($PROVEDOR)"
  python3 "$AQUI/narrar.py" roteiro.txt narracao_bruta.mp3 --provedor "$PROVEDOR" --voz "$VOZ"
  # corta pausa maior que 0,4 s (deixa 0,35 s): o ritmo fica de vídeo curto
  ffmpeg -y -v error -i narracao_bruta.mp3 -af "silenceremove=stop_periods=-1:stop_duration=0.4:stop_threshold=-38dB:stop_silence=0.35" -ar 44100 -ac 1 -sample_fmt s16 narracao.wav
  echo "   bruta $(dur narracao_bruta.mp3) s -> sem pausas longas $(dur narracao.wav) s"
else
  echo "1. narração: reaproveitando narracao.wav ($(dur narracao.wav) s)"
fi

echo "2. transcrição palavra por palavra"
python3 "$AQUI/transcrever.py" narracao.wav whisper.json
echo "3. alinhando a legenda ao roteiro"
python3 alinhar.py

D=$(python3 -c "print(round($(dur narracao.wav)+1.0,1))")
echo "4. render 3D ($D s)"
python3 -m http.server 8765 --bind 127.0.0.1 >/dev/null 2>&1 & SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
for _ in 1 2 3 4 5 6 7 8 9 10; do curl -s -o /dev/null http://127.0.0.1:8765/cena.html && break; sleep 0.5; done
node render.js "$D"

echo "5. efeitos e mixagem"
python3 mix.py "$D"
ffmpeg -y -v error -i video_mudo.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af "loudnorm=I=-15:TP=-1.0:LRA=11" -ar 44100 -c:a aac -b:a 192k -shortest video.mp4

FONTE=""
for f in "$HOME/Library/Fonts/Montserrat-Bold.ttf" /Library/Fonts/Montserrat-Bold.ttf /usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf "$HOME/.fonts/Montserrat-Bold.ttf"; do [ -f "$f" ] && FONTE="$f" && break; done
if [ -s wm.txt ] && [ -n "$FONTE" ]; then
  echo "6. marca d'água ($(cat wm.txt))"
  # textfile= em vez de text='@...': o @ e as aspas quebram o drawtext
  WM="drawtext=fontfile=$FONTE:textfile=wm.txt:fontsize=44:fontcolor=white@0.9:borderw=3:bordercolor=black@0.35:shadowcolor=black@0.35:shadowx=0:shadowy=3:x=(w-text_w)/2:y=1560"
  ffmpeg -y -v error -i video.mp4 -vf "$WM" -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a copy -movflags +faststart video_final.mp4
else
  echo "6. sem marca d'água (wm.txt vazio ou fonte Montserrat Bold não instalada)"; cp video.mp4 video_final.mp4
fi

echo "7. folha de conferência (6 quadros)"
TMP=$(mktemp -d); i=0
for f in 0.04 0.2 0.4 0.6 0.78 0.92; do
  t=$(python3 -c "print(round($D*$f,2))")
  ffmpeg -v error -y -ss "$t" -i video_final.mp4 -frames:v 1 -vf scale=270:-1 "$TMP/q$i.png"; i=$((i+1))
done
ffmpeg -v error -y -i "$TMP/q0.png" -i "$TMP/q1.png" -i "$TMP/q2.png" -i "$TMP/q3.png" -i "$TMP/q4.png" -i "$TMP/q5.png" -filter_complex hstack=inputs=6 -q:v 3 quadros.jpg
rm -rf "$TMP"

echo
echo "pronto: $P/video_final.mp4 | vídeo $(ffprobe -v error -select_streams v -show_entries stream=duration -of default=nw=1:nk=1 video_final.mp4) s, áudio $(ffprobe -v error -select_streams a -show_entries stream=duration -of default=nw=1:nk=1 video_final.mp4) s"
echo "confira quadros.jpg: a palavra da legenda tem que bater com o que aparece na cena."
