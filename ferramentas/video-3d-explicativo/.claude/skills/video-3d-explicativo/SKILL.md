---
name: video-3d-explicativo
description: Faz vídeo vertical 3D explicativo (estilo animação de cidadezinha low poly, 1080x1920, 30 a 60 s) com narração por IA, legenda palavra por palavra sincronizada, câmera que acompanha a fala, etiquetas, efeitos sonoros e marca d'água. Tudo roda no próprio computador, sem editor de vídeo. Use quando o pedido for "vídeo 3D", "vídeo explicativo animado", "vídeo estilo animação explicando X", "transforma esse roteiro em vídeo 3D", "troca a voz do vídeo 3D", "refaz com outra voz", ou para virar um conceito (de tráfego, de negócio, de produto) em Reels/Shorts.
---

# Vídeo 3D explicativo

O vídeo é uma página HTML com uma cena three.js. O Playwright fotografa a página quadro a quadro, a
30 fps, e o ffmpeg junta os quadros com a narração. Tudo o que acontece na tela (mudança de câmera,
etiqueta, objeto que aparece) fica preso a uma **palavra do roteiro**. Quando a voz diz "círculo", o
círculo aparece. É isso que deixa o vídeo sincronizado, sem edição manual.

```
roteiro.txt -> narração (API de voz) -> corte de pausas -> whisper (tempo de cada palavra)
  -> alinhar.py (tempos.js: WORDS da legenda + MK, o tempo das palavras-chave)
  -> cena.html (usa MK) -> render.js (quadros) -> mix.py (efeitos) -> loudnorm -> marca d'água
```

Onde ficam os arquivos: instalada com `./instalar.sh --global`, em `~/.claude/skills/video-3d-explicativo/`
(ou `~/.codex/skills/...`); usada de dentro do repositório, na raiz dele. Nos comandos abaixo, `scripts/`
e `modelo/` são relativos a essa pasta.

Antes do primeiro vídeo, rode `./instalar.sh` (no repositório) para ver o que falta no ambiente.

Arquivos:
- `modelo/`: projeto pronto do exemplo "anúncio de negócio local" (cena, alinhador, mix, render, roteiro).
- `scripts/fazer_video.sh`: roda o pipeline inteiro em uma pasta de vídeo.
- `scripts/narrar.py`: narração pelo fish.audio ou pela ElevenLabs.
- `scripts/transcrever.py`: whisper com tempo por palavra (mlx-whisper, faster-whisper ou openai-whisper).

## Passo a passo

### 1. Pasta do vídeo
Copie `modelo/` para uma pasta nova (ex.: `~/videos-3d/<tema>/`). Nunca trabalhe dentro de `modelo/`.

### 2. Roteiro (`roteiro.txt`)
- 30 a 55 s falados (~110 a 150 palavras). Frase curta, uma ideia por frase, fala de gente.
- Primeira frase = gancho com a dor concreta ("Tem gente a três quilômetros da sua loja procurando o que você vende").
- Escreva o roteiro **junto com o plano de cena**: cada mudança visual precisa de uma palavra-âncora no texto.
- Escreva os números por extenso ("três", "vinte"). O whisper devolve dígito e o alinhador resolve isso,
  mas a âncora no `alinhar.py` tem que ser a palavra como está no roteiro.
- Sem tags de emoção na legenda. O `narrar.py` remove `[sarcastic]` e afins antes de enviar.

### 3. Palavras-chave (`alinhar.py`, dicionário `keys`)
Cada entrada é `'nome': ('palavra', ocorrência)`. A cena usa `MK.nome`, o segundo em que a palavra é
dita. Se a palavra aparece mais de uma vez no roteiro, indique qual ocorrência é (ex.: `('Manda', 2)`).
Se faltar uma palavra no roteiro, o script para com "marca não achada" e diz qual.

### 4. Cena (`cena.html`), só se o tema mudou
Mantenha o **motor** e troque o **conteúdo**:
- Motor (não mexa): `renderAt(t)` determinístico (todo estado depende só de `t`, nunca de relógio),
  `window.ready`, `window.SFX` (lista de `{t, k}`, com k = pop, plop, tap, coin ou whoosh), a legenda
  (`#cap` lendo `WORDS`), a câmera por keyframes `K = [[tempo, [posição], [alvo]], ...]` e o `pop()`/`ease()`.
- Conteúdo (troque): os objetos (casas, loja, pessoas, celular, moedas), as etiquetas `pills`
  (texto, cor, posição 3D `at` ou de tela `scr`, entrada `t0` e saída `t1` em MK) e os keyframes de câmera.
- Para conferir sem renderizar tudo: suba o servidor (`python3 -m http.server 8765 --bind 127.0.0.1` na
  pasta) e rode `node render.js 50 2,11,21,35`. Isso gera `prev_<t>.jpg` em segundos. Olhe as prévias
  antes do render completo.

### 5. Voz
- fish.audio: crie a conta, gere a chave em API Keys e exporte `FISH_API_KEY`. O ID da voz é o final
  da URL (`fish.audio/pt/m/<ID>/`). O modelo `s2.1-pro-free` gera sem gastar crédito.
- ElevenLabs: `ELEVENLABS_API_KEY` e o voice_id, com o modelo `eleven_multilingual_v2`.
- **Direito de voz:** voz de personagem, dublador ou famoso da comunidade (ex.: a voz de um personagem de anime)
  serve só para **teste interno do formato**. Em post, anúncio ou peça de cliente, use voz original
  da biblioteca ou a sua própria voz clonada. Usar a voz de outra pessoa sem autorização dá processo,
  e anúncio com voz de famoso tende a ser reprovado.
- Combine voz e roteiro. Voz calma pede roteiro neutro, voz de vilão pede roteiro provocador. Se
  trocar o tom, reescreva o texto mantendo as palavras-âncora.

### 6. Rodar
```
scripts/fazer_video.sh ~/videos-3d/<tema> --voz <ID> [--provedor fish|elevenlabs] [--refazer-narracao]
```
O render leva cerca de 1 min para cada 50 s de vídeo num Mac M1. Para trocar só a voz depois:
mesmo comando com `--voz <outro ID> --refazer-narracao`.

### 7. Conferir antes de entregar (obrigatório)
1. Abra `quadros.jpg` (6 quadros) e confira se a palavra da legenda em cada quadro bate com o que a
   cena mostra e com o trecho do `whisper.json` naquele segundo.
2. Confira se a transcrição impressa no passo 2 contém o roteiro inteiro. Uma frase faltando quer
   dizer que a voz engoliu um trecho: gere de novo.
3. Confira se a duração de vídeo e a de áudio batem (a última linha do script mostra as duas).
4. Confira se a marca d'água está acima da área de botões do Reels (y=1560 em 1920 já fica).

## Armadilhas conhecidas
- `ERR_CONNECTION_REFUSED` no render: o servidor da porta 8765 não está rodando **dentro da pasta do
  vídeo**. O `fazer_video.sh` sobe e derruba sozinho. Se rodar à mão, suba antes e depois feche
  com `pkill -f "http.server 8765"`.
- Marca d'água com `text='@perfil'` quebra o drawtext. Use `textfile=wm.txt`.
- ElevenLabs `eleven_v3` ignora a velocidade, e as tags deixam a fala lenta. Corrija com `atempo`
  (1,1 a 1,25) no ffmpeg, depois do `silenceremove`.
- Legenda adiantada ou atrasada costuma ser âncora errada (ocorrência trocada) ou palavra que o
  whisper ouviu diferente. Olhe o `whisper.json` naquele trecho.
- Em Linux ou Windows sem GPU, o render fica mais lento (swiftshader), mas funciona.
