---
name: subidor-campanha
description: Sobe uma campanha Meta completa (campanha + conjuntos + anúncios + criativos) a partir de um briefing em linguagem natural e dos criativos no Google Drive ou numa pasta local. Toda campanha nasce PAUSADA. Use quando o pedido for "sobe a campanha do cliente X", "cria a estrutura de teste pra Y", "monta a campanha com esses criativos", "duplica o vencedor", ou quando precisar subir vídeo/imagem — porque o conector da Meta sozinho não sobe mídia do Drive e cria em rascunho que publica ligado.
---

# Subidor de campanha

Transforma briefing + criativos em estrutura completa no Gerenciador. **Nunca liga nada.**

## Regra inviolável

Toda campanha criada nasce `PAUSED`. Ligar é decisão do gestor, depois de conferir, e vale para
conta própria e de cliente. Nunca chamar `ads_activate_entity` com `publish_as_active: true` nesta
skill, nunca mexer em verba de campanha que já está no ar, nunca comprar nada.

## Passo 0 — Achar a conta no cadastro

Nunca usar ID de conta solto que veio no meio da conversa. Ler `clientes.json` (na pasta desta
skill; modelo em `clientes.exemplo.json`), casar o nome ou apelido do cliente e pegar `conta`,
`pagina`, `instagram`, o pixel do produto certo, `ticket` e `url_tags`. Cliente que não está no
cadastro: perguntar os IDs e sugerir incluir.

Pixel é **por produto** em vários checkouts. Conta com mais de um pixel: confirmar qual antes de
criar o conjunto, porque o evento de conversão não edita depois.

## Passo 1 — Fechar o briefing (não adivinhar)

Se faltar campo obrigatório, perguntar tudo de uma vez, numa mensagem só.

| Campo | Padrão se não disserem |
|---|---|
| Objetivo | `OUTCOME_SALES`, evento `PURCHASE` |
| Ticket do produto | **obrigatório**: define verba e CPA de corte |
| Fase | teste de criativo, validação de estrutura ou escala |
| Verba/dia | teste: 1/3 do ticket **por criativo**; validação: 1× o ticket por estrutura; escala: mínimo 3× o ticket |
| Estrutura | CBO com um conjunto e N criativos (`1-1-N`), salvo pedido de ABO |
| Público | aberto (BR, 18–65, `location_types` home+recent) na fase de teste |
| Pixel | do cadastro; se ambíguo, `ads_get_datasets` e confirmar |
| Criativos | pasta do Drive ou pasta local; um anúncio por arquivo |
| Destino | URL da página + `url_tags` copiado da conta |
| Texto, título e CTA | do briefing; sem texto, pedir. Não inventar promessa |

CPA de corte, para quem vai ligar robô de otimização depois: ponto de partida = **metade do que
entra no caixa por venda** (líquido, não o preço de tabela). Produto com upsell/backend forte
aguenta teto maior.

## Passo 2 — Ler a conta antes de nomear

Listar as campanhas que já existem (`ads_get_ad_entities`, `level: "campaign"`,
`fields: ["id","name"]`) e o `url_tags` de um anúncio que está no ar. Copiar o padrão de nome e de
UTM de lá. Conta nova: usar `references/nomenclatura.md`.

## Passo 3 — Plano por escrito, aprovado antes de qualquer escrita

Mandar ao gestor, antes da primeira chamada que cria algo:

```
Conta: <nome> (act_...) · Página · Instagram · Pixel <id> evento PURCHASE
Campanha: <nome com tags> · CBO R$ 99/dia
  Conjunto: ABERTO | BR 25-65 | ADV+ OFF
    AD01-depoimento (vídeo 4:5)   → https://... 
    AD02-lista      (vídeo 9:16)  → https://...
url_tags: <copiado da campanha X>
Nasce: tudo pausado.
```

Só seguir com o "ok".

## Passo 4 — Trazer os criativos para o disco

A Graph e o conector da Meta não sobem a partir de link do Drive: o arquivo precisa estar local.
Do Drive: `search_files` na pasta do cliente → `download_file_content`, ou `rclone` se tiver.
Guardar numa pasta `criativos/` ao lado do plano. O nome do arquivo vira o nome do anúncio
(`AD01-depoimento.mp4` → anúncio `AD01-depoimento`).

Antes de subir, conferir cada arquivo com `ffprobe`: proporção (9:16 só entrega em Reels/Stories),
duração e tamanho (acima de ~100 MB o script usa o envio resumável sozinho).

## Passo 5 — Escolher a rota

| Rota | Quando | Observação |
|---|---|---|
| **A. `scripts/meta_subir.py` (Graph API)** | padrão | cria tudo PAUSED de verdade, sobe vídeo grande, retoma se cair |
| B. Conector da Meta (MCP) | sem token próprio, ou criativo barrado por 1885183 | cria em RASCUNHO que publica ATIVO: ver `references/armadilhas-meta.md`, seção Status |
| C. OneClick (`copyReferenceCampaign` / `createAdsInAdSet`) | conta já otimizada pelo OneClick, duplicar vencedor | aceita link do Drive; conferir `instagram_user_id` no lote |
| D. Navegador (Playwright) | último recurso | só o que nenhuma API faz |

Mistura que resolve o 1885183 (app em modo desenvolvimento): mídia, campanha e conjunto pela rota A;
criativo pelo conector da Meta (`ads_create_creative`); cole o `creative_id` no plano e rode a rota A
de novo, que ela cria só o anúncio.

## Passo 6 — Subir pela rota A

1. Montar o `plano.json` a partir do plano aprovado (modelo em `scripts/plano.exemplo.json`).
2. Simular: `python3 scripts/meta_subir.py estrutura plano.json --simular`. Ler as chamadas,
   principalmente a verba em centavos e o `url_tags`.
3. Subir: `python3 scripts/meta_subir.py estrutura plano.json`. Se parar num erro, ele diz qual,
   guarda o que já criou em `plano.ids.json` e continua dali na próxima rodada. Procure o código em
   `references/armadilhas-meta.md` antes de tentar de novo.

`"ligar_pela_campanha": true` no plano faz conjunto e anúncio nascerem ACTIVE embaixo da campanha
PAUSED: nada gasta, os anúncios já entram em revisão e ligar vira um clique só. Usar só se o gestor
pedir.

## Passo 7 — Provar que subiu (verificação, não afirmação)

Obrigatório antes de dizer "pronto":

1. `python3 scripts/meta_subir.py conferir <campaign_id>`: status dos três níveis, verba, evento,
   `location_types`, link, `url_tags`, perfil do Instagram e pendência de revisão de cada anúncio.
   Saída com "PROBLEMAS" = não está pronto.
2. `ads_get_ad_preview` de cada anúncio, se tiver o conector da Meta, para ter a prévia.
3. `ads_get_errors` na conta, se tiver o conector.

Fechar com a árvore criada (campanha → conjuntos → anúncios), os IDs, o link do Gerenciador e a
frase explícita: **tudo pausado, nada gastando. Para ligar: <exatamente o que falta ligar>.**
Campanha ACTIVE com todos os anúncios pausados é campanha morta: dizer os níveis que faltam.

## Passo 8 — Robô de otimização (opcional, sugerir)

Se a conta usa OneClick, oferecer `createOptimization` apontando o CPA de pausa definido no passo 1.
Criar a otimização é seguro: ela só age depois que a campanha for ligada. Lembrar que duplicar a
campanha no Gerenciador depois deixa a cópia sem o robô.

## Referências

- `references/nomenclatura.md`: tags do nome, UTM, tags de controle do OneClick.
- `references/armadilhas-meta.md`: erros com código e o que resolve.
