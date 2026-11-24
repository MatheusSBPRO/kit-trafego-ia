"""Servidor MCP por stdio, só com a biblioteca padrão (Python 3.9+).

Fala JSON-RPC 2.0, uma mensagem por linha: initialize (com negociação de protocolVersion),
notifications/initialized, ping, tools/list e tools/call. O que o servidor escreve no stdout é só
protocolo; qualquer print perdido vai para o stderr, que o cliente trata como log.
"""
import io
import json
import sys
import traceback

from . import __version__
from .ferramentas import POR_NOME, definicoes, executar, sem_token

VERSOES = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
COM_ESTRUTURA = {"2025-11-25", "2025-06-18"}   # versões que conhecem structuredContent

INSTRUCOES = (
    "Ferramentas do kit-trafego-ia para gestor de tráfego. checar_criativo e simular_campanha não precisam de "
    "token. subir_campanha, subir_midia e conferir_campanha usam META_TOKEN do ambiente. Tudo o que sobe para a "
    "Meta nasce PAUSADO e não há opção para ligar. Ordem recomendada: checar_criativo, simular_campanha, "
    "mostrar a simulação para a pessoa aprovar, subir_campanha, conferir_campanha."
)

AJUDA = f"""kit-trafego-ia {__version__}: servidor MCP (stdio) com as ferramentas de tráfego do kit.

Uso:
  kit-trafego-ia              abre o servidor MCP no stdio (é o que o Claude Code e o Codex chamam)
  kit-trafego-ia --version    mostra a versão
  kit-trafego-ia --help       esta ajuda

Claude Code:  claude mcp add kit-trafego -- uvx kit-trafego-ia
Token da Meta: variável de ambiente META_TOKEN (só para subir e conferir).
Código e documentação: https://github.com/MatheusSBPRO/kit-trafego-ia
"""


def _erro(id_, codigo, mensagem):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": codigo, "message": mensagem}}


def _ok(id_, resultado):
    return {"jsonrpc": "2.0", "id": id_, "result": resultado}


class Servidor:
    def __init__(self, saida):
        self.saida = saida
        self.versao = VERSOES[0]

    def enviar(self, msg):
        self.saida.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.saida.flush()

    def tratar(self, msg):
        """Devolve a resposta (dict) ou None quando a mensagem é notificação ou resposta do cliente."""
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            return _erro(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
        metodo = msg.get("method")
        tem_id = "id" in msg
        if metodo is None:
            return None if tem_id else _erro(None, -32600, "Invalid Request")   # resposta do cliente: ignora
        if not isinstance(metodo, str):
            return _erro(msg.get("id"), -32600, "Invalid Request")
        if not tem_id:
            return None   # notificação (initialized, cancelled...): não tem resposta
        id_ = msg["id"]
        params = msg.get("params") or {}
        if not isinstance(params, dict):
            return _erro(id_, -32602, "Invalid params")
        try:
            if metodo == "initialize":
                return _ok(id_, self.inicializar(params))
            if metodo == "ping":
                return _ok(id_, {})
            if metodo == "tools/list":
                return _ok(id_, {"tools": definicoes()})
            if metodo == "tools/call":
                return self.chamar(id_, params)
            return _erro(id_, -32601, f"Method not found: {metodo}")
        except Exception as e:  # nunca derruba o servidor
            traceback.print_exc(file=sys.stderr)
            return _erro(id_, -32603, sem_token(f"Internal error: {e}"))

    def inicializar(self, params):
        pedida = params.get("protocolVersion")
        self.versao = pedida if pedida in VERSOES else VERSOES[0]
        return {
            "protocolVersion": self.versao,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "kit-trafego-ia", "title": "Kit de tráfego com IA", "version": __version__},
            "instructions": INSTRUCOES,
        }

    def chamar(self, id_, params):
        nome = params.get("name")
        if nome not in POR_NOME:
            return _erro(id_, -32602, f"Ferramenta desconhecida: {nome}")
        argumentos = params.get("arguments") or {}
        if not isinstance(argumentos, dict):
            return _erro(id_, -32602, "arguments precisa ser um objeto")
        try:
            texto, dados, falhou = executar(nome, argumentos)
        except Exception as e:  # erro inesperado do script vira resultado com isError, como pede o MCP
            traceback.print_exc(file=sys.stderr)
            texto, dados, falhou = sem_token(f"Erro inesperado em {nome}: {e}"), None, True
        resultado = {"content": [{"type": "text", "text": texto}], "isError": bool(falhou)}
        if dados is not None and self.versao in COM_ESTRUTURA:
            resultado["structuredContent"] = dados
        return _ok(id_, resultado)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if any(a in ("--version", "-V") for a in argv):
        print(f"kit-trafego-ia {__version__}")
        return 0
    if argv:
        print(AJUDA)
        return 0 if any(a in ("--help", "-h") for a in argv) else 2

    entrada = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    saida = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
    sys.stdout = sys.stderr   # print perdido vai para o log, não quebra o protocolo
    srv = Servidor(saida)
    while True:
        linha = entrada.readline()
        if not linha:
            return 0
        linha = linha.strip()
        if not linha:
            continue
        try:
            msg = json.loads(linha)
        except ValueError:
            srv.enviar(_erro(None, -32700, "Parse error"))
            continue
        if isinstance(msg, list):   # lote (protocolo 2025-03-26)
            if not msg:
                srv.enviar(_erro(None, -32600, "Invalid Request"))
                continue
            respostas = [r for r in (srv.tratar(m) for m in msg) if r is not None]
            if respostas:
                srv.enviar(respostas)
            continue
        resposta = srv.tratar(msg)
        if resposta is not None:
            srv.enviar(resposta)


if __name__ == "__main__":
    sys.exit(main())
