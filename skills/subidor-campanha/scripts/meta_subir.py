#!/usr/bin/env python3
"""Sobe campanha Meta pela Graph API. Nada sai ligado.

  python3 meta_subir.py estrutura plano.json [--simular]   campanha, conjuntos, criativos e anúncios
  python3 meta_subir.py midia act_123 arq1.mp4 arq2.jpg    só sobe a mídia (vídeo id / image hash)
  python3 meta_subir.py conferir <campaign_id>             lê o que subiu e aponta o que está errado

Token: variável META_TOKEN, ou META_TOKEN=... no arquivo .env da pasta da skill.
Só usa a biblioteca padrão do Python (3.9+).

`estrutura` grava os ids em <plano>.ids.json e retoma dali: se cair no meio, rode de novo que ele
não recria o que já existe. `--simular` imprime cada chamada sem tocar na Meta (não pede token).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

V = os.environ.get("META_API_VERSION", "v23.0")
API = f"https://graph.facebook.com/{V}"
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO = (".mp4", ".mov", ".m4v", ".avi", ".webm")
LIMITE_SIMPLES = 90 * 1024 * 1024   # acima de ~100 MB o envio simples volta vazio: vai resumável
SIMULAR = False
_TOKEN = None


# ---------------------------------------------------------------- chamada

class ErroMeta(Exception):
    def __init__(self, err):
        self.err = err
        self.subcode = err.get("error_subcode")
        msg = err.get("error_user_msg") or err.get("message", "")
        super().__init__(f"{msg} (code {err.get('code')}, subcode {self.subcode})")


def token():
    global _TOKEN
    if _TOKEN:
        return _TOKEN
    _TOKEN = os.environ.get("META_TOKEN", "")
    env = os.path.join(SKILL, ".env")
    if not _TOKEN and os.path.exists(env):
        for linha in open(env, encoding="utf-8"):
            chave, _, valor = linha.strip().partition("=")
            if chave.strip() == "META_TOKEN":
                _TOKEN = valor.strip().strip("'\"")
    if not _TOKEN:
        sys.exit("Falta o META_TOKEN (variável de ambiente ou .env na pasta da skill).")
    return _TOKEN


def abre(req):
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            corpo = r.read()
    except urllib.error.HTTPError as e:
        corpo = e.read()
    if not corpo.strip():
        raise ErroMeta({"message": "a Meta respondeu vazio (arquivo grande demais para o envio simples?)"})
    out = json.loads(corpo)
    if isinstance(out, dict) and "error" in out:
        raise ErroMeta(out["error"])
    return out


def chama(metodo, caminho, params=None):
    p = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list, bool)) else v
         for k, v in (params or {}).items()}
    if SIMULAR and metodo == "POST":
        print(f"  [simular] POST /{caminho}\n" + json.dumps(params, ensure_ascii=False, indent=2))
        return {"id": f"<{caminho.split('/')[-1]}>", "success": True}
    p["access_token"] = token()
    url = f"{API}/{caminho}"
    if metodo == "GET":
        return abre(urllib.request.Request(url + "?" + urllib.parse.urlencode(p)))
    return abre(urllib.request.Request(url, data=urllib.parse.urlencode(p).encode(), method="POST"))


def envia_arquivo(caminho, campos, campo_arquivo, nome, dados):
    """POST multipart com um arquivo (a Graph não aceita link do Drive: o arquivo tem que ser local)."""
    limite = uuid.uuid4().hex
    corpo = b""
    for k, v in {**campos, "access_token": token()}.items():
        corpo += f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    corpo += (f'--{limite}\r\nContent-Disposition: form-data; name="{campo_arquivo}"; filename="{nome}"\r\n'
              f"Content-Type: application/octet-stream\r\n\r\n").encode() + dados + b"\r\n"
    corpo += f"--{limite}--\r\n".encode()
    req = urllib.request.Request(f"{API}/{caminho}", data=corpo, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={limite}"})
    return abre(req)


# ---------------------------------------------------------------- mídia

def sobe_imagem(conta, arquivo):
    nome = os.path.basename(arquivo)
    if SIMULAR:
        print(f"  [simular] imagem {nome} -> /{conta}/adimages")
        return {"tipo": "imagem", "hash": f"<hash {nome}>"}
    out = envia_arquivo(f"{conta}/adimages", {}, "filename", nome, open(arquivo, "rb").read())
    return {"tipo": "imagem", "hash": next(iter(out["images"].values()))["hash"]}


def sobe_video(conta, arquivo):
    nome = os.path.basename(arquivo)
    tamanho = os.path.getsize(arquivo)
    if SIMULAR:
        rota = "resumável" if tamanho > LIMITE_SIMPLES else "simples"
        print(f"  [simular] vídeo {nome} ({tamanho / 1e6:.0f} MB, envio {rota}) -> /{conta}/advideos")
        return {"tipo": "video", "id": f"<video {nome}>", "capa": f"<capa {nome}>"}
    if tamanho <= LIMITE_SIMPLES:
        vid = envia_arquivo(f"{conta}/advideos", {"name": nome}, "source", nome, open(arquivo, "rb").read())["id"]
    else:
        ini = chama("POST", f"{conta}/advideos", {"upload_phase": "start", "file_size": tamanho})
        sessao, vid = ini["upload_session_id"], ini["video_id"]
        de, ate = int(ini["start_offset"]), int(ini["end_offset"])
        with open(arquivo, "rb") as fh:
            while de < ate:
                fh.seek(de)
                parte = fh.read(ate - de)
                r = envia_arquivo(f"{conta}/advideos", {"upload_phase": "transfer", "upload_session_id": sessao,
                                                        "start_offset": de}, "video_file_chunk", nome, parte)
                de, ate = int(r["start_offset"]), int(r["end_offset"])
                print(f"    {nome}: {de / tamanho:.0%}")
        chama("POST", f"{conta}/advideos", {"upload_phase": "finish", "upload_session_id": sessao, "title": nome})
    espera_video(vid, nome)
    return {"tipo": "video", "id": vid, "capa": capa_do_video(vid)}


def espera_video(vid, nome, limite_s=900):
    """Criativo com vídeo ainda processando vira anúncio quebrado que só dá erro horas depois."""
    fim = time.time() + limite_s
    while time.time() < fim:
        st = chama("GET", vid, {"fields": "status"}).get("status", {}).get("video_status")
        if st == "ready":
            return
        if st == "error":
            raise ErroMeta({"message": f"a Meta recusou o vídeo {nome} no processamento"})
        time.sleep(10)
    raise ErroMeta({"message": f"o vídeo {nome} não ficou pronto em {limite_s // 60} min"})


def capa_do_video(vid):
    """Vídeo sem capa explícita é recusado no criativo (subcode 1443226). Usa a capa preferida da Meta."""
    capas = chama("GET", f"{vid}/thumbnails").get("data", [])
    preferida = next((c for c in capas if c.get("is_preferred")), capas[0] if capas else None)
    return preferida["uri"] if preferida else None


def sobe_midia(conta, arquivo):
    if not os.path.exists(arquivo):
        raise ErroMeta({"message": f"arquivo não encontrado: {arquivo}"})
    return sobe_video(conta, arquivo) if arquivo.lower().endswith(VIDEO) else sobe_imagem(conta, arquivo)


# ---------------------------------------------------------------- estrutura

def centavos(reais):
    return int(round(float(reais) * 100))


def brl(valor):
    return "R$ " + f"{float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def confere_plano(pl):
    erros = []
    for campo in ("conta", "pagina", "pixel", "campanha", "conjuntos"):
        if not pl.get(campo):
            erros.append(f"falta '{campo}' no plano")
    if not str(pl.get("conta", "")).startswith("act_"):
        erros.append("'conta' precisa do prefixo act_")
    cp = pl.get("campanha", {})
    tipo = cp.get("tipo", "CBO").upper()
    if tipo == "CBO" and not cp.get("orcamento_dia"):
        erros.append("CBO: 'orcamento_dia' vai na campanha")
    for cj in pl.get("conjuntos", []):
        if tipo == "CBO" and cj.get("orcamento_dia"):
            erros.append(f"CBO: tire 'orcamento_dia' do conjunto '{cj.get('nome')}' (vai só na campanha)")
        if tipo == "ABO" and not cj.get("orcamento_dia"):
            erros.append(f"ABO: falta 'orcamento_dia' no conjunto '{cj.get('nome')}'")
        if not cj.get("anuncios"):
            erros.append(f"conjunto '{cj.get('nome')}' sem anúncio")
        for ad in cj.get("anuncios", []):
            if not ad.get("creative_id"):
                for campo in ("nome", "midia", "texto", "link"):
                    if not ad.get(campo):
                        erros.append(f"anúncio '{ad.get('nome', '?')}' sem '{campo}'")
    if erros:
        sys.exit("Plano com problema:\n  - " + "\n  - ".join(erros))
    return tipo


def publico(cj):
    t = json.loads(json.dumps(cj.get("publico") or {"geo_locations": {"countries": ["BR"]}}))
    geo = t.setdefault("geo_locations", {"countries": ["BR"]})
    geo.setdefault("location_types", ["home", "recent"])   # sem isso o conjunto não publica (#1870194)
    t.setdefault("age_min", 18)
    t.setdefault("age_max", 65)
    # A Graph exige a escolha explícita. 1 = Advantage+ (idade e interesse viram sugestão).
    t.setdefault("targeting_automation", {"advantage_audience": int(cj.get("advantage_audience", 0))})
    return t


def criativo(pl, ad, midia):
    cta = {"type": ad.get("cta", "LEARN_MORE"), "value": {"link": ad["link"]}}
    spec = {"page_id": pl["pagina"]}
    if pl.get("instagram"):
        spec["instagram_user_id"] = pl["instagram"]
    if midia["tipo"] == "video":
        dados = {"video_id": midia["id"], "message": ad["texto"], "call_to_action": cta}
        if ad.get("titulo"):
            dados["title"] = ad["titulo"]
        if midia.get("capa_hash"):
            dados["image_hash"] = midia["capa_hash"]
        else:
            dados["image_url"] = midia["capa"]
        spec["video_data"] = dados
    else:
        dados = {"link": ad["link"], "message": ad["texto"], "image_hash": midia["hash"], "call_to_action": cta}
        if ad.get("titulo"):
            dados["name"] = ad["titulo"]
        if ad.get("descricao"):
            dados["description"] = ad["descricao"]
        spec["link_data"] = dados
    params = {"name": ad["nome"], "object_story_spec": spec}
    if pl.get("url_tags"):
        params["url_tags"] = pl["url_tags"]
    return params


def estrutura(arquivo_plano):
    pl = json.load(open(arquivo_plano, encoding="utf-8"))
    tipo = confere_plano(pl)
    base = os.path.dirname(os.path.abspath(arquivo_plano))
    arq_ids = os.path.splitext(arquivo_plano)[0] + ".ids.json"
    ids = {} if SIMULAR or not os.path.exists(arq_ids) else json.load(open(arq_ids, encoding="utf-8"))
    ids.setdefault("midia", {})
    ids.setdefault("conjuntos", {})
    ids.setdefault("anuncios", {})

    def grava():
        if not SIMULAR:
            json.dump(ids, open(arq_ids, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    conta, cp = pl["conta"], pl["campanha"]
    # Padrão: tudo PAUSED. Com "ligar_pela_campanha": true, conjunto e anúncio nascem ACTIVE embaixo da
    # campanha PAUSED: nada gasta, os anúncios já entram em revisão e ligar vira um clique só.
    filho = "ACTIVE" if pl.get("ligar_pela_campanha") else "PAUSED"

    print(f"Conta {conta} · {tipo} · campanha PAUSED, conjuntos e anúncios {filho}")
    if tipo == "CBO":
        print(f"Verba: {brl(cp['orcamento_dia'])}/dia na campanha = {centavos(cp['orcamento_dia'])} centavos")
    else:
        for cj in pl["conjuntos"]:
            print(f"Verba: {brl(cj['orcamento_dia'])}/dia em '{cj['nome']}' = {centavos(cj['orcamento_dia'])} centavos")

    try:
        if "campanha" not in ids:
            p = {"name": cp["nome"], "objective": cp.get("objetivo", "OUTCOME_SALES"), "status": "PAUSED",
                 "special_ad_categories": cp.get("categorias_especiais", []), "buying_type": "AUCTION"}
            if tipo == "CBO":
                p["daily_budget"] = centavos(cp["orcamento_dia"])
                p["bid_strategy"] = cp.get("lance", "LOWEST_COST_WITHOUT_CAP")
            else:
                # Sem isso a ABO dá 4834011. false: conjunto não rouba 20% da verba do outro no teste.
                p["is_adset_budget_sharing_enabled"] = False
            ids["campanha"] = chama("POST", f"{conta}/campaigns", p)["id"]
            grava()
        print(f"campanha {ids['campanha']}  {cp['nome']}")

        for cj in pl["conjuntos"]:
            if cj["nome"] not in ids["conjuntos"]:
                p = {"name": cj["nome"], "campaign_id": ids["campanha"], "status": filho,
                     "optimization_goal": cj.get("otimizacao", "OFFSITE_CONVERSIONS"), "billing_event": "IMPRESSIONS",
                     "promoted_object": {"pixel_id": pl["pixel"], "custom_event_type": cj.get("evento", "PURCHASE")},
                     "targeting": publico(cj)}
                if tipo == "ABO":
                    p["daily_budget"] = centavos(cj["orcamento_dia"])
                    p["bid_strategy"] = cj.get("lance", "LOWEST_COST_WITHOUT_CAP")
                if cj.get("inicio"):
                    p["start_time"] = cj["inicio"]   # só vale na criação: depois que passa, não edita (1487057)
                ids["conjuntos"][cj["nome"]] = chama("POST", f"{conta}/adsets", p)["id"]
                grava()
            cj_id = ids["conjuntos"][cj["nome"]]
            print(f"  conjunto {cj_id}  {cj['nome']}")

            for ad in cj["anuncios"]:
                chave = f"{cj['nome']} / {ad['nome']}"
                if chave in ids["anuncios"]:
                    print(f"    anúncio {ids['anuncios'][chave]}  {ad['nome']} (já existia)")
                    continue
                cr_id = ad.get("creative_id")
                if not cr_id:
                    caminho = os.path.join(base, ad["midia"])
                    if ad["midia"] not in ids["midia"]:
                        m = sobe_midia(conta, caminho)
                        if m["tipo"] == "video" and ad.get("capa"):
                            m["capa_hash"] = sobe_imagem(conta, os.path.join(base, ad["capa"]))["hash"]
                        ids["midia"][ad["midia"]] = m
                        grava()
                    try:
                        cr_id = chama("POST", f"{conta}/adcreatives", criativo(pl, ad, ids["midia"][ad["midia"]]))["id"]
                    except ErroMeta as e:
                        if e.subcode == 1885183:
                            raise ErroMeta({"message": (
                                "o app do seu token está em modo de desenvolvimento e a Meta barra o criativo. "
                                "Ponha o app em modo Live, ou crie o criativo pelo conector da Meta "
                                "(ads_create_creative) e cole o id em \"creative_id\" deste anúncio no plano"),
                                "error_subcode": 1885183})
                        raise
                ids["anuncios"][chave] = chama("POST", f"{conta}/ads", {
                    "name": ad["nome"], "adset_id": cj_id, "creative": {"creative_id": cr_id}, "status": filho})["id"]
                grava()
                print(f"    anúncio {ids['anuncios'][chave]}  {ad['nome']}")
    except ErroMeta as e:
        grava()
        sys.exit(f"\nParou: {e}\nO que já subiu está em {arq_ids}. Corrija e rode de novo: ele continua dali.")

    if SIMULAR:
        print("\nSimulação: nada foi enviado à Meta.")
        return
    print(f"\nPronto, nada ligado. Ids em {arq_ids}.\nConfira: python3 {sys.argv[0]} conferir {ids['campanha']}")


# ---------------------------------------------------------------- conferir

def lista(caminho, campos):
    out, pagina = [], chama("GET", caminho, {"fields": campos, "limit": 200})
    while True:
        out += pagina.get("data", [])
        prox = pagina.get("paging", {}).get("next")
        if not prox:
            return out
        pagina = abre(urllib.request.Request(prox))


def conferir(campanha_id):
    cp = chama("GET", campanha_id, {"fields": "name,account_id,status,effective_status,objective,daily_budget,"
                                              "lifetime_budget,bid_strategy"})
    cjs = lista(f"{campanha_id}/adsets", "name,status,effective_status,daily_budget,optimization_goal,"
                                         "promoted_object,targeting,start_time")
    ads = lista(f"{campanha_id}/ads", "name,status,effective_status,adset_id,issues_info,"
                                      "creative{id,url_tags,object_story_spec}")
    problemas = []
    verba = cp.get("daily_budget") or cp.get("lifetime_budget")
    print(f"CAMPANHA {cp['id']}  {cp['name']}\n  {cp['status']} / {cp['effective_status']} · {cp['objective']}"
          + (f" · {brl(int(verba) / 100)}" if verba else " · verba nos conjuntos (ABO)"))

    for cj in cjs:
        geo = cj.get("targeting", {}).get("geo_locations", {})
        verba_cj = f" · {brl(int(cj['daily_budget']) / 100)}/dia" if cj.get("daily_budget") else ""
        evento = cj.get("promoted_object", {}).get("custom_event_type", "-")
        print(f"\n  CONJUNTO {cj['id']}  {cj['name']}\n    {cj['status']} / {cj['effective_status']}"
              f" · {cj.get('optimization_goal')} · evento {evento}{verba_cj} · início {cj.get('start_time', '-')}")
        if not geo.get("location_types"):
            problemas.append(f"conjunto '{cj['name']}' sem location_types: não vai publicar (#1870194)")
        for ad in (a for a in ads if a["adset_id"] == cj["id"]):
            cr = ad.get("creative", {})
            spec = cr.get("object_story_spec", {})
            dados = spec.get("video_data") or spec.get("link_data") or {}
            link = dados.get("link") or dados.get("call_to_action", {}).get("value", {}).get("link", "-")
            print(f"    ANÚNCIO {ad['id']}  {ad['name']}\n      {ad['status']} / {ad['effective_status']}"
                  f" · criativo {cr.get('id', '-')}\n      link {link}\n      url_tags {cr.get('url_tags') or '-'}")
            if not cr.get("url_tags"):
                problemas.append(f"anúncio '{ad['name']}' sem url_tags (rastreio não chega; url_tags não edita depois)")
            if spec and not (spec.get("instagram_user_id") or spec.get("instagram_actor_id")):
                problemas.append(f"anúncio '{ad['name']}' sem perfil do Instagram (vai sair só com a Página)")
            for issue in ad.get("issues_info") or []:
                problemas.append(f"anúncio '{ad['name']}': {issue.get('error_message')}")
    if not ads:
        problemas.append("a campanha não tem anúncio")

    print(f"\nLink: https://adsmanager.facebook.com/adsmanager/manage/ads?act={cp['account_id']}"
          f"&selected_campaign_ids={campanha_id}")
    print("\nNADA GASTANDO." if cp["status"] == "PAUSED" else "\nATENÇÃO: a campanha está ATIVA.")
    pausados = sum(1 for c in cjs if c["status"] == "PAUSED") + sum(1 for a in ads if a["status"] == "PAUSED")
    if cp["status"] == "PAUSED":
        print("Para ligar: a campanha" + (f" + {pausados} conjunto(s)/anúncio(s) pausado(s)" if pausados else " (só ela)"))
    if problemas:
        print("\nPROBLEMAS:\n  - " + "\n  - ".join(problemas))
        sys.exit(1)
    print("Sem problema encontrado.")


# ---------------------------------------------------------------- linha de comando

def main():
    global SIMULAR
    args = [a for a in sys.argv[1:] if a != "--simular"]
    SIMULAR = "--simular" in sys.argv
    if len(args) >= 2 and args[0] == "estrutura":
        estrutura(args[1])
    elif len(args) >= 3 and args[0] == "midia":
        for arq in args[2:]:
            try:
                print(os.path.basename(arq), json.dumps(sobe_midia(args[1], arq), ensure_ascii=False))
            except ErroMeta as e:
                print(f"{os.path.basename(arq)}  ERRO: {e}")
    elif len(args) == 2 and args[0] == "conferir":
        conferir(args[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
