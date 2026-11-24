#!/usr/bin/env python3
"""Varredura de dado sensível: falha se achar no repositório algo que não pode ser público.

  python3 testes/varredura.py          varre os arquivos do repositório (versionados e novos, sem os ignorados)

O que barra: caminho de pasta de usuário do Mac, ID de conta de anúncio, token da Meta e IDs do
WhatsApp (contato @lid e grupo @g.us). ID de exemplo só com zeros (act_000000000000000) passa.

Ocorrência legítima (um filtro de SQL, uma regra escrita no CONTRIBUTING) entra em
testes/varredura-permitidos.txt, uma por linha, no formato:  caminho :: linha exata
Quem revisa o PR vê a linha nova nesse arquivo.
Código de saída: 0 sem achado, 1 com achado.
"""
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PERMITIDOS = RAIZ / "testes" / "varredura-permitidos.txt"
IGNORAR = {"testes/varredura.py", "testes/varredura-permitidos.txt"}
PADROES = [
    ("caminho de pasta de usuário do Mac", re.compile(r"/Users/")),
    ("ID de conta de anúncio", re.compile(r"act_(?!0+\b)[0-9]{6,}")),
    ("token da Meta", re.compile(r"EAA[A-Za-z0-9]{20,}")),
    ("ID de contato do WhatsApp", re.compile(r"@lid")),
    ("ID de grupo do WhatsApp", re.compile(r"@g\.us")),
]


def arquivos():
    try:
        cmd = ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
        saida = subprocess.run(cmd, cwd=RAIZ, capture_output=True, check=True).stdout
        return [n for n in saida.decode("utf-8").split("\0") if n]
    except (OSError, subprocess.CalledProcessError):
        return [str(p.relative_to(RAIZ)) for p in RAIZ.rglob("*") if p.is_file() and ".git" not in p.parts]


def permitidos():
    ok = set()
    if PERMITIDOS.exists():
        for linha in PERMITIDOS.read_text(encoding="utf-8").splitlines():
            if linha.strip() and not linha.startswith("#") and " :: " in linha:
                caminho, _, trecho = linha.partition(" :: ")
                ok.add((caminho.strip(), trecho.strip()))
    return ok


def main():
    ok = permitidos()
    achados = []
    for nome in arquivos():
        if nome in IGNORAR:
            continue
        p = RAIZ / nome
        try:
            dados = p.read_bytes()
        except OSError:
            continue
        if b"\0" in dados[:8000]:   # binário
            continue
        for n, linha in enumerate(dados.decode("utf-8", errors="ignore").splitlines(), 1):
            for rotulo, rx in PADROES:
                if rx.search(linha) and (nome, linha.strip()) not in ok:
                    mascarada = rx.sub(lambda m: m.group(0)[:6] + "***", linha.strip())   # o log do CI é público
                    achados.append(f"{nome}:{n}: {rotulo}: {mascarada[:160]}")
    if achados:
        print("Varredura achou dado que não pode entrar no repositório:\n")
        print("\n".join(achados))
        print("\nTire o dado (use um exemplo com zeros, como act_000000000000000) ou, se for uso legítimo, "
              "ponha a linha em testes/varredura-permitidos.txt e explique no PR.")
        return 1
    print("Varredura: nada sensível encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
