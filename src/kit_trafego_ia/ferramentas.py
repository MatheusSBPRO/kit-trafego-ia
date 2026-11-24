"""As ferramentas do servidor MCP.

Nenhuma regra de negócio mora aqui. Cada ferramenta chama o script de origem, que é a fonte única:

  ferramentas/checar-criativo-meta/scripts/checar_criativo.py      (e referencias/termos.json)
  ferramentas/subir-campanha-meta/skills/subidor-campanha/scripts/meta_subir.py

No pacote instalado, os três arquivos entram pelo build em kit_trafego_ia/_ferramentas/. Rodando do
código do repositório, eles são lidos direto das pastas acima.

Travas que valem para todas as ferramentas da Meta:
  - o token sai só da variável de ambiente META_TOKEN, nunca de argumento, e é apagado de toda saída;
  - tudo nasce PAUSADO: plano com "ligar_pela_campanha" é recusado e qualquer escrita com status
    diferente de PAUSED é barrada antes de sair;
  - a simulação não acessa a rede.
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import tempfile
import unicodedata
import uuid
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EMBUTIDO = AQUI / "_ferramentas"
RAIZ_REPO = AQUI.parent.parent
ORIGEM = {
    "meta_subir.py": "ferramentas/subir-campanha-meta/skills/subidor-campanha/scripts/meta_subir.py",
    "checar_criativo.py": "ferramentas/checar-criativo-meta/scripts/checar_criativo.py",
    "termos.json": "ferramentas/checar-criativo-meta/referencias/termos.json",
}
VAR_TOKEN = "META_TOKEN"
ORDEM = ("FORA", "REVISAR", "PENDENTE", "LIMPO")


class ErroFerramenta(Exception):
    """Erro que volta ao cliente como resultado com isError, e não como falha do protocolo."""


# ---------------------------------------------------------------- scripts de origem

def caminho(nome):
    for p in (EMBUTIDO / nome, RAIZ_REPO / ORIGEM[nome]):
        if p.is_file():
            return p
    raise ErroFerramenta(f"não achei {nome} (nem no pacote, nem em {ORIGEM[nome]})")


def carregar(nome):
    """Carrega o script de novo a cada chamada: token e modo simulação não passam de uma chamada a outra."""
    arq = caminho(nome)
    spec = importlib.util.spec_from_file_location(f"kit_trafego_ia_{arq.stem}_{uuid.uuid4().hex}", str(arq))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sem_token(texto):
    """Apaga o token de qualquer texto que volte ao cliente."""
    t = os.environ.get(VAR_TOKEN, "").strip()
    if len(t) >= 8:
        texto = texto.replace(t, "***")
    texto = re.sub(r"(access_token=)[^&\s\"']+", r"\1***", texto)
    return re.sub(r"EAA[A-Za-z0-9]{20,}", "EAA***", texto)


def rodar(func, *args):
    """Roda uma função do script guardando o que ela imprime. sys.exit vira retorno, não derruba o servidor."""
    saida = io.StringIO()
    codigo = 0
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida):
        try:
            func(*args)
        except SystemExit as e:
            if isinstance(e.code, str):
                print(e.code)
                codigo = 1
            else:
                codigo = e.code or 0
    return codigo, sem_token(saida.getvalue()).strip()


def lista(valor):
    if valor is None or valor == "":
        return []
    if isinstance(valor, (list, tuple)):
        return [str(v) for v in valor if str(v).strip()]
    return [str(valor)]


# ---------------------------------------------------------------- checar_criativo

def checar_criativo(args):
    mod = carregar("checar_criativo.py")
    termos = os.environ.get("KIT_TRAFEGO_IA_TERMOS") or str(caminho("termos.json"))
    regras = mod.carregar_regras(termos)
    por_que = {cat["id"]: cat.get("por_que", "") for cat, _ in regras}
    itens = []

    def registrar(nome, origem, texto, problema=None):
        if texto is None:
            itens.append({"item": nome, "origem": origem, "veredito": "PENDENTE", "problema": problema, "achados": []})
            return
        achados = mod.checar(texto, regras)
        for a in achados:
            a["por_que"] = por_que.get(a["categoria"], "")
        itens.append({"item": nome, "origem": origem, "veredito": mod.veredito(achados), "achados": achados})

    for campo, origem in (("texto", "texto solto"), ("copy", "copy"), ("titulo", "título")):
        for i, t in enumerate(lista(args.get(campo)), 1):
            registrar(f"{campo} {i}", origem, t)
    for u in lista(args.get("url")):
        if not re.match(r"^https?://", u, re.I):
            registrar(f"página: {u}", "página de destino", None, "a url precisa começar com http:// ou https://")
            continue
        try:
            registrar(f"página: {u}", "página de destino", mod.texto_da_pagina(u))
        except Exception as e:  # página fora do ar também é motivo de reprovação
            registrar(f"página: {u}", "página de destino", None, f"não abriu ({e})")
    existentes = []
    for e in lista(args.get("arquivos")):
        p = Path(e).expanduser()
        if p.exists():
            existentes.append(str(p))
        else:
            registrar(e, "arquivo", None, "não achei esse arquivo ou pasta")
    for arq in mod.listar_arquivos(existentes):
        texto, origem, problema = mod.texto_do_arquivo(arq, bool(args.get("transcrever", False)))
        registrar(arq.name, origem, texto, problema)

    if not itens:
        raise ErroFerramenta("Mande pelo menos um de: texto, copy, titulo, url ou arquivos.")

    cont = {v: sum(1 for i in itens if i["veredito"] == v) for v in ORDEM}
    geral = next(v for v in ORDEM if cont[v]) if itens else "LIMPO"
    linhas = [f"Veredito geral: {geral}", ""]
    for item in itens:
        linhas.append(f"{item['veredito']:<8} {item['item']}  ({item['origem']})")
        if item.get("problema"):
            linhas.append(f"    {item['problema']}")
        explicadas = set()
        for a in item["achados"]:
            linhas.append(f"    [{a['severidade']}] {a['nome']}: \"{a['achou']}\"")
            linhas.append(f"        {a['trecho']}")
            if a["categoria"] not in explicadas and a["por_que"]:
                explicadas.add(a["categoria"])
                linhas.append(f"        Por quê: {a['por_que']}")
    linhas += ["", f"Resumo: {cont['FORA']} fora · {cont['REVISAR']} revisar · {cont['PENDENTE']} pendente · "
                   f"{cont['LIMPO']} limpo",
               "O filtro acha palavra, não intenção: leia os trechos marcados no contexto antes de decidir. "
               "LIMPO não garante aprovação."]
    return "\n".join(linhas), {"veredito_geral": geral, "resumo": cont, "itens": itens}


# ---------------------------------------------------------------- plano de campanha

def _normal(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _ler_plano(args):
    """Devolve (plano, pasta base das mídias, caminho do arquivo ou None)."""
    plano, arquivo = args.get("plano"), args.get("arquivo_plano")
    if bool(plano) == bool(arquivo):
        raise ErroFerramenta("Mande 'plano' (o JSON do plano) ou 'arquivo_plano' (caminho do .json), um dos dois.")
    if arquivo:
        p = Path(arquivo).expanduser().resolve()
        if not p.is_file():
            raise ErroFerramenta(f"não achei o arquivo do plano: {arquivo}")
        try:
            plano = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            raise ErroFerramenta(f"o arquivo do plano não é um JSON válido: {e}")
        base = p.parent
    else:
        if isinstance(plano, str):
            try:
                plano = json.loads(plano)
            except ValueError as e:
                raise ErroFerramenta(f"o plano não é um JSON válido: {e}")
        base = Path(args.get("pasta_midia") or os.getcwd()).expanduser().resolve()
        p = None
    if not isinstance(plano, dict):
        raise ErroFerramenta("o plano precisa ser um objeto JSON (veja plano.exemplo.json)")
    return plano, base, p


def _conferir_travas(plano):
    if plano.get("ligar_pela_campanha"):
        raise ErroFerramenta("Plano recusado: 'ligar_pela_campanha' não é aceito pelo kit. Tudo nasce PAUSADO "
                             "(campanha, conjuntos e anúncios). Tire o campo, ou deixe false, e rode de novo. "
                             "Quem liga é você, no Gerenciador, depois de conferir.")
    erros = []
    nomes_cj = [cj.get("nome") for cj in plano.get("conjuntos") or [] if isinstance(cj, dict)]
    for nome in sorted({n for n in nomes_cj if nomes_cj.count(n) > 1 and n}):
        erros.append(f"dois conjuntos com o mesmo nome '{nome}': o script retoma pelo nome e juntaria os dois")
    for cj in plano.get("conjuntos") or []:
        if not isinstance(cj, dict):
            continue
        nomes_ad = [ad.get("nome") for ad in cj.get("anuncios") or [] if isinstance(ad, dict)]
        for nome in sorted({n for n in nomes_ad if nomes_ad.count(n) > 1 and n}):
            erros.append(f"dois anúncios com o mesmo nome '{nome}' no conjunto '{cj.get('nome')}'")
    if erros:
        raise ErroFerramenta("Plano com problema:\n  - " + "\n  - ".join(erros))


def _midias_absolutas(plano, base):
    for cj in plano.get("conjuntos") or []:
        for ad in (cj.get("anuncios") or []) if isinstance(cj, dict) else []:
            for campo in ("midia", "capa"):
                v = ad.get(campo) if isinstance(ad, dict) else None
                if v and not os.path.isabs(os.path.expanduser(v)):
                    ad[campo] = str(base / v)
                elif v:
                    ad[campo] = os.path.expanduser(v)


def _trava_pausado(mod):
    """Barra, antes de sair para a Meta, qualquer escrita com status diferente de PAUSED."""
    original = mod.chama

    def chama(metodo, caminho_api, params=None):
        if metodo.upper() == "POST":
            st = (params or {}).get("status")
            if st is not None and st != "PAUSED":
                raise mod.ErroMeta({"message": f"bloqueado pelo kit: escrita com status {st}. Tudo nasce PAUSADO."})
        return original(metodo, caminho_api, params)

    mod.chama = chama


def _sem_rede(mod):
    def bloqueado(*_a, **_k):
        raise mod.ErroMeta({"message": "a simulação não acessa a Meta"})

    mod.abre = bloqueado
    mod.token = lambda: "simulacao-sem-token"


def _token_do_ambiente():
    t = os.environ.get(VAR_TOKEN, "").strip()
    if not t:
        raise ErroFerramenta("Falta o token da Meta. Defina a variável de ambiente META_TOKEN na configuração do "
                             "servidor MCP (veja o README do kit). O token nunca vai em argumento.")
    return t


def _meta_real():
    _token_do_ambiente()
    mod = carregar("meta_subir.py")
    mod.token = _token_do_ambiente
    mod.SIMULAR = False
    _trava_pausado(mod)
    return mod


def simular_campanha(args):
    plano, base, arquivo = _ler_plano(args)
    _conferir_travas(plano)
    mod = carregar("meta_subir.py")
    mod.SIMULAR = True
    _sem_rede(mod)
    _trava_pausado(mod)
    with tempfile.TemporaryDirectory(prefix="kit-trafego-ia-") as tmp:
        if arquivo is None:
            _midias_absolutas(plano, base)
            arquivo = Path(tmp) / "plano.json"
            arquivo.write_text(json.dumps(plano, ensure_ascii=False), encoding="utf-8")
        codigo, texto = rodar(mod.estrutura, str(arquivo))
    ok = codigo == 0 and "Simulação: nada foi enviado à Meta." in texto
    cabeca = ("Plano válido. Simulação abaixo: nenhuma chamada foi feita à Meta.\n\n" if ok
              else "A simulação parou. Corrija o plano e rode de novo.\n\n")
    return cabeca + texto, {"ok": ok, "saida": texto}, not ok


def _pasta_estado():
    return Path(os.environ.get("KIT_TRAFEGO_IA_DIR") or (Path.home() / ".kit-trafego-ia")).expanduser()


def subir_campanha(args):
    plano, base, arquivo = _ler_plano(args)
    _conferir_travas(plano)
    mod = _meta_real()
    if arquivo is None:
        _midias_absolutas(plano, base)
        nome = _normal(f"{plano.get('conta', '')}-{(plano.get('campanha') or {}).get('nome', '')}")
        slug = re.sub(r"[^a-z0-9]+", "-", nome).strip("-")[:90] or "plano"
        pasta = _pasta_estado() / "planos"
        pasta.mkdir(parents=True, exist_ok=True)
        arquivo = pasta / f"{slug}.json"
        arquivo.write_text(json.dumps(plano, ensure_ascii=False, indent=2), encoding="utf-8")
    codigo, texto = rodar(mod.estrutura, str(arquivo))
    ids = Path(os.path.splitext(str(arquivo))[0] + ".ids.json")
    dados = {"ok": codigo == 0, "arquivo_ids": str(ids), "saida": texto}
    if ids.is_file():
        try:
            dados["ids"] = json.loads(ids.read_text(encoding="utf-8"))
        except ValueError:
            pass
    rodape = (f"\n\nIds guardados em {ids}. Se parou no meio, chame de novo com o mesmo plano: ele continua dali."
              "\nPróximo passo: conferir_campanha com o id da campanha. Nada foi ligado.")
    return texto + rodape, dados, codigo != 0


def subir_midia(args):
    conta = str(args.get("conta") or "")
    if not re.match(r"^act_[0-9]+$", conta):
        raise ErroFerramenta("'conta' precisa ser o id da conta de anúncio com o prefixo act_")
    arquivos = lista(args.get("arquivos"))
    if not arquivos:
        raise ErroFerramenta("Mande pelo menos um caminho em 'arquivos'.")
    mod = _meta_real()
    resultado, linhas, falhou = [], [], False
    for arq in arquivos:
        p = os.path.expanduser(arq)
        saida = io.StringIO()
        try:
            with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida):
                m = mod.sobe_midia(conta, p)
            resultado.append({"arquivo": arq, **m})
            linhas.append(f"{os.path.basename(p)}  {json.dumps(m, ensure_ascii=False)}")
        except mod.ErroMeta as e:
            falhou = True
            resultado.append({"arquivo": arq, "erro": sem_token(str(e))})
            linhas.append(f"{os.path.basename(p)}  ERRO: {sem_token(str(e))}")
    return "\n".join(linhas), {"midias": resultado}, falhou


def conferir_campanha(args):
    cid = str(args.get("campanha_id") or "").strip()
    if not re.match(r"^[0-9]+$", cid):
        raise ErroFerramenta("'campanha_id' precisa ser o id numérico da campanha")
    mod = _meta_real()
    try:
        codigo, texto = rodar(mod.conferir, cid)
    except mod.ErroMeta as e:
        raise ErroFerramenta(f"a Meta respondeu com erro: {sem_token(str(e))}")
    return texto, {"sem_problema": codigo == 0, "saida": texto}, False


# ---------------------------------------------------------------- definições

_PLANO = {
    "plano": {"type": "object", "description": "O plano em JSON, no formato de plano.exemplo.json: conta (act_...), "
              "pagina, instagram, pixel, url_tags, campanha {nome, objetivo, tipo CBO|ABO, orcamento_dia em reais} e "
              "conjuntos [{nome, evento, publico, anuncios [{nome, midia, texto, titulo, link, cta}]}]."},
    "arquivo_plano": {"type": "string", "description": "Caminho de um plano .json no disco, no lugar de 'plano'. "
                      "As mídias são lidas em relação à pasta do arquivo."},
    "pasta_midia": {"type": "string", "description": "Com 'plano': pasta onde estão as mídias com caminho relativo. "
                    "Padrão: a pasta em que o servidor foi aberto."},
}

FERRAMENTAS = [
    {
        "name": "checar_criativo",
        "title": "Checar criativo contra a política da Meta",
        "description": "Passa texto, copy, título, página de destino ou arquivos (vídeo, imagem, .txt) pela lista de "
                       "termos que costumam dar reprovação ou bloqueio na Meta. Devolve FORA (risco alto, reescreva), "
                       "REVISAR (depende do contexto), LIMPO (nada no filtro) ou PENDENTE (sem texto para checar), "
                       "com o trecho e o motivo de cada achado. Não precisa de token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "texto": {"type": "string", "description": "Qualquer texto solto: fala do vídeo, texto da arte."},
                "copy": {"type": "string", "description": "Texto principal do anúncio."},
                "titulo": {"type": "string", "description": "Título ou descrição do anúncio."},
                "url": {"type": "string", "description": "Página de destino (http ou https). O texto da página é baixado e checado."},
                "arquivos": {"type": "array", "items": {"type": "string"},
                             "description": "Arquivos ou pastas. Vídeo usa <nome>.txt ao lado ou transcreve; imagem usa <nome>.txt ao lado."},
                "transcrever": {"type": "boolean", "description": "Transcrever vídeo sem .txt com o whisper local (lento). Padrão: false."},
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
        "funcao": checar_criativo,
    },
    {
        "name": "simular_campanha",
        "title": "Simular a subida de uma campanha (sem tocar na Meta)",
        "description": "Valida o plano da campanha e mostra cada chamada que a subida faria, com a verba em centavos. "
                       "Não acessa a Meta, não pede token e não grava nada. Rode sempre antes de subir_campanha.",
        "inputSchema": {"type": "object", "properties": _PLANO},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
        "funcao": simular_campanha,
    },
    {
        "name": "subir_campanha",
        "title": "Subir campanha na Meta, tudo PAUSADO",
        "description": "Cria campanha, conjuntos, criativos e anúncios pela Graph API. Tudo nasce PAUSADO e não existe "
                       "opção para ligar: quem liga é a pessoa, no Gerenciador. Se cair no meio, chamar de novo com o "
                       "mesmo plano continua de onde parou. Precisa de META_TOKEN no ambiente do servidor.",
        "inputSchema": {"type": "object", "properties": _PLANO},
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
        "funcao": subir_campanha,
    },
    {
        "name": "subir_midia",
        "title": "Subir vídeo ou imagem para a conta de anúncio",
        "description": "Sobe arquivos locais para a biblioteca da conta e devolve o id do vídeo (com a capa) ou o hash "
                       "da imagem. Vídeo grande vai pelo envio resumável. Não cria anúncio. Precisa de META_TOKEN.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "conta": {"type": "string", "description": "Conta de anúncio com o prefixo act_."},
                "arquivos": {"type": "array", "items": {"type": "string"}, "description": "Caminhos dos arquivos locais."},
            },
            "required": ["conta", "arquivos"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
        "funcao": subir_midia,
    },
    {
        "name": "conferir_campanha",
        "title": "Conferir uma campanha que subiu",
        "description": "Lê a campanha, os conjuntos e os anúncios e aponta o que está errado: conjunto sem "
                       "location_types, anúncio sem url_tags ou sem perfil do Instagram, problema de revisão. "
                       "Só leitura. Precisa de META_TOKEN.",
        "inputSchema": {
            "type": "object",
            "properties": {"campanha_id": {"type": "string", "description": "Id numérico da campanha."}},
            "required": ["campanha_id"],
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
        "funcao": conferir_campanha,
    },
]

POR_NOME = {f["name"]: f for f in FERRAMENTAS}


def definicoes():
    return [{k: v for k, v in f.items() if k != "funcao"} for f in FERRAMENTAS]


def executar(nome, argumentos):
    """Devolve (texto, dados, is_error). Erro conhecido vira resultado com is_error, nunca exceção."""
    f = POR_NOME[nome]
    try:
        resposta = f["funcao"](argumentos or {})
    except ErroFerramenta as e:
        return sem_token(str(e)), None, True
    if len(resposta) == 2:
        texto, dados = resposta
        return texto, dados, False
    return resposta
