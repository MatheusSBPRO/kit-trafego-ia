#!/usr/bin/env python3
"""Gera a narração do roteiro por API de voz.

    python3 narrar.py roteiro.txt saida.mp3 --provedor fish --voz <ID_DO_MODELO>
    python3 narrar.py roteiro.txt saida.mp3 --provedor elevenlabs --voz <VOICE_ID>

Chaves no ambiente: FISH_API_KEY (fish.audio) ou ELEVENLABS_API_KEY (ElevenLabs).
No fish.audio, o ID é o final da URL da voz: fish.audio/pt/m/<ID>/
Tags de emoção entre colchetes ([sarcastic], [sighs]...) são removidas antes de enviar,
porque a legenda sai do roteiro e não pode mostrar a tag.
"""
import argparse, json, os, re, sys, urllib.error, urllib.request


def fish(txt, voz, modelo):
    chave = os.environ.get('FISH_API_KEY') or sys.exit('Falta FISH_API_KEY no ambiente (fish.audio > API Keys).')
    corpo = {'text': txt, 'reference_id': voz, 'format': 'mp3', 'mp3_bitrate': 192, 'normalize': True, 'latency': 'normal'}
    return urllib.request.Request('https://api.fish.audio/v1/tts', data=json.dumps(corpo).encode(), headers={
        'Authorization': 'Bearer ' + chave, 'Content-Type': 'application/json', 'model': modelo})


def elevenlabs(txt, voz, modelo):
    chave = os.environ.get('ELEVENLABS_API_KEY') or sys.exit('Falta ELEVENLABS_API_KEY no ambiente.')
    corpo = {'text': txt, 'model_id': modelo}
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voz}?output_format=mp3_44100_192'
    return urllib.request.Request(url, data=json.dumps(corpo).encode(), headers={
        'xi-api-key': chave, 'Content-Type': 'application/json'})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('roteiro'); ap.add_argument('saida')
    ap.add_argument('--provedor', choices=['fish', 'elevenlabs'], default='fish')
    ap.add_argument('--voz', required=True)
    ap.add_argument('--modelo', help='fish: s2.1-pro-free (padrão, sem crédito) ou s1 | elevenlabs: eleven_multilingual_v2 (padrão)')
    a = ap.parse_args()
    txt = re.sub(r'\[[^\]]+\]\s?', '', open(a.roteiro, encoding='utf-8').read()).strip()
    if a.provedor == 'fish':
        req = fish(txt, a.voz, a.modelo or 's2.1-pro-free')
    else:
        req = elevenlabs(txt, a.voz, a.modelo or 'eleven_multilingual_v2')
    try:
        dados = urllib.request.urlopen(req, timeout=300).read()
    except urllib.error.HTTPError as e:
        sys.exit(f'Erro {e.code} da API de voz: {e.read()[:400]!r}')
    open(a.saida, 'wb').write(dados)
    print('narração ok:', a.saida, len(dados) // 1024, 'KB')


if __name__ == '__main__':
    main()
