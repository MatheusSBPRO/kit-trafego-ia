#!/usr/bin/env python3
"""Transcreve a narração palavra por palavra -> whisper.json ([[palavra, início, fim], ...]).

    python3 transcrever.py narracao.wav whisper.json

Usa o primeiro que estiver instalado: mlx-whisper (Mac M1+), faster-whisper ou openai-whisper.
"""
import json, sys

entrada, saida = sys.argv[1], sys.argv[2]
ws = None
try:
    import mlx_whisper
    r = mlx_whisper.transcribe(entrada, path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='pt', word_timestamps=True)
    ws = [[w['word'].strip(), round(w['start'], 2), round(w['end'], 2)] for s in r['segments'] for w in s.get('words', [])]
    texto = r['text']
except ImportError:
    try:
        from faster_whisper import WhisperModel
        segs, _ = WhisperModel('large-v3', compute_type='int8').transcribe(entrada, language='pt', word_timestamps=True)
        segs = list(segs)
        ws = [[w.word.strip(), round(w.start, 2), round(w.end, 2)] for s in segs for w in (s.words or [])]
        texto = ' '.join(s.text for s in segs)
    except ImportError:
        try:
            import whisper
            r = whisper.load_model('large-v3').transcribe(entrada, language='pt', word_timestamps=True)
            ws = [[w['word'].strip(), round(w['start'], 2), round(w['end'], 2)] for s in r['segments'] for w in s.get('words', [])]
            texto = r['text']
        except ImportError:
            sys.exit('Nenhum whisper instalado. Mac M1+: pip install mlx-whisper | outros: pip install faster-whisper')
json.dump(ws, open(saida, 'w'), ensure_ascii=False)
print(len(ws), 'palavras |', texto.strip())
