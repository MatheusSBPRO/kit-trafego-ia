#!/usr/bin/env python3
"""Teste de ponta a ponta do servidor MCP, falando JSON-RPC pelo stdin como o Claude Code fala.

  python3 testes/testar_mcp.py                                  testa o código da pasta src/
  python3 testes/testar_mcp.py kit-trafego-ia                   testa o comando instalado
  python3 testes/testar_mcp.py uvx --from dist/<wheel> kit-trafego-ia

Roda sem token e sem rede para a Meta: o META_TOKEN é tirado do ambiente do servidor, a simulação
não acessa a rede e o teste de subir_campanha só confere que ele recusa sem token.
Código de saída: 0 se tudo passou, 1 se algo falhou.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FRASE_FORA = "Ganhe R$ 300 por dia sem sair de casa, renda extra garantida"
FRASE_LIMPA = "Aula prática de planilha para organizar os gastos da casa"
NOMES = {"checar_criativo", "simular_campanha", "subir_campanha", "subir_midia", "conferir_campanha"}


def plano_exemplo():
    """Plano no formato de plano.exemplo.json, com ids de exemplo (zeros) e mídia de mentira."""
    return {
        "conta": "act_000000000000000",
        "pagina": "000000000000000",
        "instagram": "17841400000000000",
        "pixel": "000000000000000",
        "url_tags": "utm_source=facebook&utm_medium={{adset.name}}&utm_campaign={{campaign.name}}&utm_content={{ad.name}}",
        "campanha": {"nome": "[TESTE][VENDAS][CBO][FRIO]", "objetivo": "OUTCOME_SALES", "tipo": "CBO",
                     "orcamento_dia": 99.0},
        "conjuntos": [{
            "nome": "ABERTO | BR 25-65",
            "evento": "PURCHASE",
            "publico": {"geo_locations": {"countries": ["BR"]}, "age_min": 25, "age_max": 65},
            "anuncios": [
                {"nome": "AD01-video", "midia": "AD01.mp4", "capa": "AD01-capa.jpg", "texto": "Texto do anúncio.",
                 "titulo": "Garanta seu ingresso", "link": "https://exemplo.com.br/ingresso", "cta": "LEARN_MORE"},
                {"nome": "AD02-imagem", "midia": "AD02.jpg", "texto": "Texto do anúncio.",
                 "link": "https://exemplo.com.br/ingresso", "cta": "SIGN_UP"},
            ],
        }],
    }


def mensagens(pasta_midia):
    plano = plano_exemplo()
    ligado = plano_exemplo()
    ligado["ligar_pela_campanha"] = True
    repetido = plano_exemplo()
    repetido["conjuntos"].append(json.loads(json.dumps(repetido["conjuntos"][0])))
    chamar = lambda i, nome, args: {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                                    "params": {"name": nome, "arguments": args}}
    return [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "testar_mcp", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        chamar(3, "checar_criativo", {"texto": FRASE_FORA}),
        chamar(4, "checar_criativo", {"texto": FRASE_LIMPA}),
        chamar(5, "simular_campanha", {"plano": plano, "pasta_midia": str(pasta_midia)}),
        chamar(6, "simular_campanha", {"plano": ligado, "pasta_midia": str(pasta_midia)}),
        chamar(7, "simular_campanha", {"plano": repetido, "pasta_midia": str(pasta_midia)}),
        chamar(8, "subir_campanha", {"plano": plano, "pasta_midia": str(pasta_midia)}),
        {"jsonrpc": "2.0", "id": 9, "method": "ping"},
        {"jsonrpc": "2.0", "id": 10, "method": "metodo/que/nao/existe"},
        chamar(11, "ferramenta_que_nao_existe", {}),
        {"jsonrpc": "2.0", "id": 12, "method": "initialize",
         "params": {"protocolVersion": "1999-01-01", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
    ]


def main():
    comando = sys.argv[1:] or [sys.executable, "-m", "kit_trafego_ia"]
    env = {k: v for k, v in os.environ.items() if k != "META_TOKEN"}
    # Rede para fora apontada para uma porta morta: se algo tentar falar com a Meta, falha em vez de chegar lá.
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        env[var] = "http://127.0.0.1:9"
    env.pop("NO_PROXY", None)
    env.pop("no_proxy", None)
    if not sys.argv[1:]:
        env["PYTHONPATH"] = str(RAIZ / "src") + os.pathsep + env.get("PYTHONPATH", "")
    falhas, passou = [], []

    def confere(nome, condicao, detalhe=""):
        (passou if condicao else falhas).append(nome if condicao else f"{nome}: {detalhe}")

    with tempfile.TemporaryDirectory() as tmp:
        midia = Path(tmp) / "midia"
        midia.mkdir()
        for nome in ("AD01.mp4", "AD01-capa.jpg", "AD02.jpg"):
            (midia / nome).write_bytes(b"arquivo de teste, nao e midia de verdade")
        env["KIT_TRAFEGO_IA_DIR"] = str(Path(tmp) / "estado")
        entrada = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in mensagens(midia))
        proc = subprocess.run(comando, input=entrada.encode("utf-8"), capture_output=True, env=env, timeout=180)
        sobrou_estado = (Path(tmp) / "estado").exists()

    saida = proc.stdout.decode("utf-8", errors="replace")
    respostas = {}
    for linha in saida.splitlines():
        try:
            msg = json.loads(linha)
        except ValueError:
            falhas.append(f"stdout tem linha que não é JSON-RPC: {linha[:120]!r}")
            continue
        respostas[msg.get("id")] = msg
    confere("servidor encerra com código 0 no fim do stdin", proc.returncode == 0, f"código {proc.returncode}")

    def resultado(i):
        return (respostas.get(i) or {}).get("result") or {}

    def texto(i):
        return "".join(c.get("text", "") for c in resultado(i).get("content", []))

    ini = resultado(1)
    confere("initialize devolve a versão pedida (2025-06-18)", ini.get("protocolVersion") == "2025-06-18", ini)
    confere("initialize anuncia a capacidade tools", "tools" in ini.get("capabilities", {}), ini)
    confere("uma resposta por pedido, nenhuma para a notificação", sorted(respostas, key=str) == sorted(range(1, 13), key=str),
            sorted(respostas, key=str))
    nomes = {t["name"] for t in resultado(2).get("tools", [])}
    confere("tools/list tem as 5 ferramentas", nomes == NOMES, sorted(nomes))
    confere("tools/list: todas com inputSchema", all("inputSchema" in t for t in resultado(2).get("tools", [])))

    fora = resultado(3).get("structuredContent", {})
    confere("checar_criativo: frase de promessa de ganho dá FORA", fora.get("veredito_geral") == "FORA", texto(3)[:300])
    confere("checar_criativo: FORA traz o motivo", "Por quê:" in texto(3), texto(3)[:300])
    limpo = resultado(4).get("structuredContent", {})
    confere("checar_criativo: frase neutra dá LIMPO", limpo.get("veredito_geral") == "LIMPO", texto(4)[:300])

    sim = texto(5)
    confere("simular_campanha: termina sem erro", resultado(5).get("isError") is False, sim[:400])
    confere("simular_campanha: nada enviado à Meta", "Simulação: nada foi enviado à Meta." in sim, sim[:400])
    confere("simular_campanha: campanha PAUSED", "campanha PAUSED" in sim, sim[:400])
    confere("simular_campanha: conjuntos e anúncios PAUSED", "conjuntos e anúncios PAUSED" in sim, sim[:400])
    confere("simular_campanha: verba em centavos (9900)", "9900 centavos" in sim, sim[:400])
    confere("simular_campanha: nenhum status ACTIVE", "ACTIVE" not in sim, sim[:400])
    confere("simular_campanha: recusa 'ligar_pela_campanha'",
            resultado(6).get("isError") is True and "PAUSADO" in texto(6), texto(6)[:300])
    confere("simular_campanha: recusa conjunto com nome repetido",
            resultado(7).get("isError") is True and "mesmo nome" in texto(7), texto(7)[:300])
    confere("subir_campanha sem token: recusa antes de qualquer chamada",
            resultado(8).get("isError") is True and "META_TOKEN" in texto(8), texto(8)[:300])
    confere("subir_campanha sem token: não grava plano", not sobrou_estado)
    confere("ping responde {}", resultado(9) == {}, respostas.get(9))
    confere("método desconhecido dá -32601", (respostas.get(10) or {}).get("error", {}).get("code") == -32601,
            respostas.get(10))
    confere("ferramenta desconhecida dá -32602", (respostas.get(11) or {}).get("error", {}).get("code") == -32602,
            respostas.get(11))
    confere("versão desconhecida cai na mais nova suportada",
            resultado(12).get("protocolVersion") == "2025-11-25", resultado(12))

    print(f"Comando: {' '.join(comando)}")
    for p in passou:
        print(f"  ok     {p}")
    for f in falhas:
        print(f"  FALHOU {f}")
    erro = proc.stderr.decode("utf-8", errors="replace").strip()
    if falhas and erro:
        print("\nstderr do servidor:\n" + erro[-2000:])
    print(f"\n{len(passou)} ok, {len(falhas)} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
