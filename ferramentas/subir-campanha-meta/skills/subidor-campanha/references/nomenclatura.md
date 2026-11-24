# Nomenclatura e UTM

## Regra zero: copie a conta, não esta página

Antes de nomear qualquer coisa, leia os nomes das campanhas que **já estão no ar na mesma conta**
(`ads_get_ad_entities` com `level: "campaign"` e `fields: ["id","name"]`, ou o Gerenciador) e siga
o padrão de lá. O nome é como o gestor lê a conta de relance. Inventar código de lançamento
(`[ABC26]`) numa conta em que todas as campanhas usam `[XYZ]` quebra filtro, relatório e robô de
otimização.

O padrão abaixo serve para conta nova, sem histórico.

## Campanha: tags em colchetes, ordem fixa

```
[LANÇAMENTO][TIPO][PRODUTO][CBO|ABO][PÚBLICO][ESTRUTURA][CRIATIVO][OTIMIZAÇÃO][CTA]
```

| # | Tag | Exemplo | O que é |
|---|---|---|---|
| 1 | lançamento | `[LANC01]` `[OUT26]` | código do lançamento ou da oferta |
| 2 | tipo | `[VENDAS]` `[LEADS]` | objetivo da campanha |
| 3 | produto | `[INGRESSO]` `[MENTORIA]` | o que está sendo vendido |
| 4 | orçamento | `[CBO]` `[ABO]` | onde mora a verba |
| 5 | público | `[FRIO]` `[QUENTE]` `[RMKT]` | temperatura |
| 6 | estrutura | `[1-1-1]` `[1-1-6]` `[1-5-1]` | campanha-conjuntos-anúncios |
| 7 | criativo | `[AD09-cinema]` | **só em 1-1-1**; em estrutura com vários criativos, omita |
| 8 | otimização | `[MAX CONV]` `[CUSTO ALVO]` | lance do conjunto |
| 9 | CTA | `[SAIBA MAIS]` `[COMPRAR]` | botão |

Exemplos:

```
[LANC01][VENDAS][INGRESSO][CBO][FRIO][1-1-1][AD09-cinema][MAX CONV][SAIBA MAIS]
[LANC01][VENDAS][INGRESSO][CBO][FRIO][1-1-6][MAX CONV][SAIBA MAIS]
```

Se o lance pedido não pôde ser aplicado (ex.: Maximizar valor bloqueado em business novo), o nome
diz o que a campanha **faz**, não o que foi pedido.

## Anúncio: `ADxx-descrição`

O nome do arquivo do criativo já carrega o sufixo (`AD01-depoimento.mp4`) e vira o nome do anúncio.
Um anúncio por criativo, sempre. Empilhar criativo no mesmo anúncio mata a leitura de qual venceu.

## Conjunto

Descreve o público, de forma que dê para entender sem abrir: `ABERTO | BR 25-65 | ADV+ OFF`,
`LAL 1% COMPRADORES 180D`, `QUENTE | IC 30D + PV 30D | exc. compradores`.

## UTM (`url_tags`)

- **Replique o `url_tags` das campanhas que já estão no ar na conta.** Não invente padrão novo:
  o dashboard e o checkout leem o que já existe.
- `url_tags` não aparece na tela do Gerenciador. Confira pela API depois de subir
  (`meta_subir.py conferir`).
- `url_tags` **não edita** depois que o criativo existe (subcode 1815573). Corrigir UTM de anúncio
  no ar é criativo novo, e o anúncio volta para revisão. Decida antes de subir o lote.
- Use as macros dinâmicas para não precisar de um criativo por campanha:
  `{{campaign.name}}`, `{{adset.name}}`, `{{ad.name}}`, `{{campaign.id}}`, `{{adset.id}}`, `{{ad.id}}`.

Padrão genérico:

```
utm_source=facebook&utm_medium={{adset.name}}&utm_campaign={{campaign.name}}&utm_content={{ad.name}}
```

Quem otimiza pelo **OneClick com checkout Zouti** precisa também de `src` e `sck` no formato do
OneClick. Só `utm_*` faz a venda chegar com campanha vazia e origem "organic":

```
src=facebook-oneclick-ads|{{ad.id}}|{{adset.id}}|{{campaign.id}}|&sck=facebook-oneclick-ads|{{ad.id}}|{{adset.id}}|{{campaign.id}}|&utm_source=facebook-oneclick-ads&utm_content={{ad.id}}&utm_medium={{adset.id}}&utm_campaign={{campaign.id}}
```

## Tags de controle do OneClick (se usar)

Escritas por você no nome, travam o robô:

- `[manual]`: bloqueia tudo (duplicar, escalar, pausar). Na campanha, protege o que está dentro.
- `[não-duplicar]`: otimiza e pausa normal, mas não cria réplica.
- `[ativo-diariamente]`: impede pausa temporária dentro do dia (oferta que vende de madrugada).
- `[intraday]`: libera só escala de verba dentro do dia.

Duplicata herda a tag: cópia de estrutura `[manual]` nasce `[manual]` e nunca é otimizada.
O marcador `🤖 [OneClick ON]` é posto pela própria plataforma quando existe otimização. Escrever à
mão não liga nada.
