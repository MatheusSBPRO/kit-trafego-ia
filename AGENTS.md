# Instruções para o Codex

Este repositório é a skill **video-3d-explicativo**. Quando o pedido for um vídeo 3D explicativo
(vídeo animado vertical com narração por IA, legenda sincronizada e câmera que acompanha a fala),
leia e siga `.claude/skills/video-3d-explicativo/SKILL.md`.

- O projeto de exemplo fica em `modelo/`. Copie para uma pasta nova antes de mexer; nunca edite `modelo/`.
- O pipeline inteiro roda com `scripts/fazer_video.sh <pasta> --voz <ID>`.
- Antes de entregar, abra `quadros.jpg` e confira se a legenda de cada quadro bate com a cena.
