# subir-campanha-meta

Agente e skill do [Claude Code](https://claude.com/claude-code) para subir campanha na Meta
completa (campanha, conjuntos, criativos e anúncios) a partir de um briefing e de uma pasta de
criativos. **Tudo nasce pausado.** Quem liga é você, depois de conferir.

É o processo que roda numa agência de tráfego para infoproduto e lançamento pago, com as
armadilhas da API que custaram dinheiro ou horas entre julho e outubro de 2026 já resolvidas.

## A ordem

1. **Conta pelo cadastro.** Conta, página, Instagram e pixel saem do `clientes.json`, nunca de ID
   solto no meio da conversa.
2. **Briefing fechado.** Objetivo, ticket, fase, verba, público, pixel, criativos e destino. O que
   faltar, o agente pergunta de uma vez.
3. **Leitura da conta.** O nome e a UTM são copiados das campanhas que já estão no ar.
4. **Plano por escrito.** A árvore inteira, com verba e UTM, vai para você aprovar antes de
   qualquer escrita.
5. **Subida pausada** pela Graph API, com retomada se cair no meio.
6. **Prova.** Status dos três níveis, `location_types`, link, `url_tags`, perfil do Instagram e
   revisão de cada anúncio, com o link do Gerenciador e o que falta você ligar.

## Instalação

Requisitos: Claude Code e Python 3.9+ (o script só usa a biblioteca padrão). Também precisa de um
token da Meta com `ads_management`. Use o de um Usuário do Sistema: Business Manager → Usuários do
sistema → Gerar token, com `ads_management`, `ads_read`, `business_management`, `pages_show_list`
e `pages_read_engagement`. O app do token precisa estar em modo **Live**.

```bash
git clone https://github.com/MatheusSBPRO/subir-campanha-meta
cd subir-campanha-meta
mkdir -p ~/.claude/agents ~/.claude/skills
cp agents/subidor-campanha.md ~/.claude/agents/
cp -R skills/subidor-campanha ~/.claude/skills/
cp .env.exemplo ~/.claude/skills/subidor-campanha/.env            # cole o token aqui
cp ~/.claude/skills/subidor-campanha/clientes.exemplo.json \
   ~/.claude/skills/subidor-campanha/clientes.json                 # cadastre suas contas
```

Opcionais, que o agente usa quando estão conectados: o conector da Meta (Meta Ads MCP), o do
Google Drive (para baixar os criativos) e o do OneClick.

Depois, no Claude Code:

```
Sobe a campanha de teste do Cliente Exemplo: ingresso de R$ 97, 3 criativos da pasta
~/criativos/lanc01, CBO, público aberto, página https://seusite.com.br/ingresso
```

O agente `subidor-campanha` assume, fecha o que faltar, manda o plano e só sobe com o seu ok.

## Sem o agente: só o script

```bash
cd ~/.claude/skills/subidor-campanha/scripts
cp plano.exemplo.json plano.json                    # preencha conta, pixel, verba, criativos
python3 meta_subir.py estrutura plano.json --simular   # mostra cada chamada, não envia nada
python3 meta_subir.py estrutura plano.json             # sobe tudo pausado
python3 meta_subir.py conferir <campaign_id>           # prova o que subiu e aponta problema
python3 meta_subir.py midia act_123 video.mp4 img.jpg  # só sobe mídia (devolve id / hash)
```

O plano aceita CBO ou ABO, imagem ou vídeo, capa própria para vídeo, `creative_id` já pronto e
`start_time`. Vídeo acima de ~100 MB vai pelo envio resumável sozinho. Se parar num erro, ele
guarda o que já criou em `plano.ids.json` e continua dali na próxima rodada.

## O que tem aqui

| Caminho | O quê |
|---|---|
| `agents/subidor-campanha.md` | o agente: os três freios, a ordem e o que conferir |
| `skills/subidor-campanha/SKILL.md` | o processo em 8 passos, do cadastro à prova |
| `skills/subidor-campanha/references/nomenclatura.md` | tags do nome da campanha, UTM, tags de controle do OneClick |
| `skills/subidor-campanha/references/armadilhas-meta.md` | erros da API com código e o que resolve |
| `skills/subidor-campanha/scripts/meta_subir.py` | sobe mídia e estrutura pela Graph, tudo pausado, e confere |
| `skills/subidor-campanha/scripts/plano.exemplo.json` | modelo de plano |
| `skills/subidor-campanha/clientes.exemplo.json` | modelo de cadastro de contas |

## Avisos

- **Mexe em conta de anúncio com dinheiro real.** Rode `--simular` antes e leia a verba em
  centavos. O uso é por sua conta.
- **O conector da Meta (MCP) cria em rascunho que publica ATIVO.** Por isso a campanha e o conjunto
  saem pela Graph. Detalhes em `armadilhas-meta.md`, seção Status.
- **`.env` e `clientes.json` ficam fora do git**, porque guardam token e ID de conta. Não suba esses
  arquivos.
- **Erro 1885183 no criativo** = app do token em modo desenvolvimento. A saída está no
  `SKILL.md`, passo 5.

---

Montado pela [Blessy Mídias](https://blessymidias.com.br).
