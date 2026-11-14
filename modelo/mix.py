# Mixa a narração com efeitos sintetizados a partir do sfx.json -> mix.wav (mono 44,1 kHz, 16 bits)
import json, wave
import numpy as np

SR = 44100
DUR = float(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 44.4
rng = np.random.default_rng(7)

def ler_wav(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return x

def env(n, a=0.004, d=None):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a)
    if d: e *= np.exp(-t / d)
    return e

def chirp(f0, f1, dur, d):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(n, 0.003, d)

def pop():   return 0.9 * chirp(900, 300, 0.12, 0.04)
def plop():  return 0.6 * chirp(520, 180, 0.09, 0.025)
def tap():
    n = int(0.05 * SR); t = np.arange(n) / SR
    return 0.7 * (np.sin(2 * np.pi * 1400 * t) * 0.6 + rng.standard_normal(n) * 0.25) * env(n, 0.001, 0.008)
def coin():
    n = int(0.45 * SR); t = np.arange(n) / SR
    s = 0.5 * np.sin(2 * np.pi * 1800 * t) * env(n, 0.002, 0.12)
    s[int(0.06 * SR):] += 0.5 * np.sin(2 * np.pi * 2700 * t[:n - int(0.06 * SR)]) * env(n - int(0.06 * SR), 0.002, 0.15)
    return 0.6 * s
def whoosh():
    n = int(0.6 * SR)
    w = rng.standard_normal(n)
    # ruído rosa aproximado: filtro passa-baixa de 1 polo em cascata
    for a in (0.95, 0.8):
        y = np.empty(n); acc = 0.0
        for i in range(n):
            acc = a * acc + (1 - a) * w[i]; y[i] = acc
        w = y
    t = np.arange(n) / n
    e = np.sin(np.pi * t) ** 2
    w = w / (np.abs(w).max() + 1e-9)
    return 0.7 * w * e

GER = {'pop': pop, 'plop': plop, 'tap': tap, 'coin': coin, 'whoosh': whoosh}
GANHO = {'pop': 0.16, 'plop': 0.10, 'tap': 0.18, 'coin': 0.14, 'whoosh': 0.20}

voz = ler_wav('narracao.wav')
N = int(DUR * SR)
mix_voz = np.zeros(N, np.float32); mix_voz[:min(N, len(voz))] = voz[:N]
fx = np.zeros(N, np.float32)
for e in json.load(open('sfx.json')):
    s = GER[e['k']]().astype(np.float32) * GANHO[e['k']]
    i = int(e['t'] * SR)
    if i >= N: continue
    j = min(N, i + len(s)); fx[i:j] += s[:j - i]

# ducking leve: efeitos caem 40% onde a voz está forte
envv = np.convolve(np.abs(mix_voz), np.ones(2205) / 2205, mode='same')
duck = 1 - 0.4 * np.clip(envv / (envv.max() * 0.5), 0, 1)
out = mix_voz + fx * duck
pk = np.abs(out).max()
out *= 0.9 / pk  # normaliza o pico em -0,9 dB
with wave.open('mix.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print('mix.wav ok', round(N / SR, 2), 's, pico', round(float(np.abs(out).max()), 3))
