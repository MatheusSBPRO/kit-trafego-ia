# Armadilhas da Meta que já custaram dinheiro ou horas

Cada linha abaixo aconteceu numa conta real entre jul e out/2026. O código do erro está junto para
achar rápido quando aparecer.

## Verba e estrutura

- **Orçamento vai em centavos.** R$ 300/dia = `30000`. Errar vira R$ 3,00 ou R$ 30.000. O
  `meta_subir.py` recebe em reais e mostra a conversão antes de enviar.
- **CBO:** a verba vai na *campanha*. **ABO:** vai no *conjunto*. Nos dois ao mesmo tempo dá erro.
- **ABO exige `is_adset_budget_sharing_enabled`** explícito, senão dá subcode **4834011**. Use
  `false` em teste: com `true` os conjuntos dividem 20% da verba entre si e o A×B se contamina.
- **Limite de gasto por conjunto dentro de CBO:** a soma dos mínimos tem que ficar abaixo de ~90% da
  verba da campanha (**1885665**), e mínimo e teto do mesmo conjunto precisam de folga (**2446182**).
- **Maximizar valor (ROAS) é bloqueado em business novo** (**2446146**). Resolve verificando o negócio.

## Público

- **`location_types` é obrigatório.** Sem ele o conjunto sobe, fica PAUSED e **não publica** ao
  ativar (**1870194**). A mensagem fala em "público salvo" e despista. Use `["home","recent"]`.
- **A campanha aceita ACTIVE com o conjunto travado.** Quem olha só o nível de campanha acha que está
  entregando e não está. Depois de ligar, confira os três níveis.
- **Advantage+ Audience (`advantage_audience: 1`) transforma idade em sugestão.** Se a idade é
  trava de verdade, use `0`.
- **"Público como sugestão" também mora em `targeting_relaxation_types`.** Com
  `custom_audience: 1` o conjunto expande para fora dos públicos personalizados mesmo com Advantage+
  desligado. Em remarketing, zere: `{"lookalike": 0, "custom_audience": 0}`.
- **Público de seguidores/engajamento de outro perfil do Instagram não entra** (**3867050**). Ele
  tem que ter sido criado com o mesmo perfil que publica o anúncio.

## Datas

- **`start_time` do conjunto só se define na criação.** Depois que o horário passa, não edita
  (**1487057**). Para estrear mais tarde: crie com `start_time` no futuro, ou deixe tudo pronto com a
  campanha pausada e ligue na hora.
- **Programação de horário (day parting) em CBO só vale se a campanha nascer com
  `pacing_type: ["day_parting"]`** junto de `lifetime_budget`. Editar depois dá **2446047**, e o
  `adset_schedule` gravado no conjunto é ignorado sem aviso.
- Campanha ACTIVE com gasto zero: antes de culpar o pixel, veja se o `start_time` do conjunto está
  no futuro e se o conjunto está PAUSED.

## Conversão

- **O evento de conversão do conjunto não edita depois de publicado** (**3260011**). `promoted_object`
  errado = conjunto novo.
- **Engajamento com THRUPLAY exige `destination_type: "ON_VIDEO"`** já na criação. Sem isso o
  anúncio falha em cascata ("website URL required" e depois "promoted object required"), e como o
  `promoted_object` não edita, o conjunto tem que ser recriado.
- **WhatsApp (CTWA), erro 1487246:** o número está ligado a uma Página, não à BM, e o formato conta
  (com ou sem o 9). Teste com `execution_options=["validate_only"]` variando Página × número.

## Mídia e criativo

- **O conector da Meta (MCP) não aceita link do Drive.** Baixe o arquivo e suba pela Graph
  (`/advideos`, `/adimages`). O OneClick aceita link do Drive.
- **Vídeo acima de ~100 MB volta VAZIO no envio simples**, sem erro nenhum. Só sobe pelo envio
  resumável (start / transfer / finish). O `meta_subir.py` escolhe sozinho.
- **Vídeo ainda processando vira anúncio quebrado** que só dá erro horas depois. Espere
  `video_status: ready` antes de criar o criativo.
- **Vídeo exige capa** (`image_url` ou `image_hash` dentro de `video_data`), senão dá **1443226**.
  A capa da Meta vem em 160×160. Para capa boa, extraia um frame com `ffmpeg` e suba como imagem.
- **Vídeo 9:16 (1080×1920) só entrega em Reels e Stories.** Para o feed, suba também 4:5 ou 1:1.
- **Criativo não edita.** Trocar link ou UTM = criativo novo.
- **1885183, "post criado por app em modo de desenvolvimento":** trava só o `POST /adcreatives`
  feito com o token do seu app. Saídas: pôr o app em modo Live; ou criar **só o criativo** pelo
  conector da Meta (`ads_create_creative`, que usa outro app) e o resto pela Graph; ou criar o
  anúncio pelo OneClick (`copyReferenceCampaign` apontando para a campanha que você criou).
- **Subir dezenas de imagens seguidas estoura o limite da conta** (code 17). Espace os envios.
- **OneClick: "Ad account not found"** quase sempre é o prefixo `act_` faltando.
- **OneClick `createAdsInAdSet` às vezes cria o anúncio sem `instagram_user_id`.** Confira o lote.

## Status

- **O conector da Meta (MCP) cria em RASCUNHO, e o rascunho publica ACTIVE.** `ads_create_campaign`,
  `ads_create_ad_set` e `ads_create_ad` devolvem `status: DRAFT` com `spec.status: ACTIVE`. Ao chamar
  `ads_activate_entity`, sai ligado. Para manter a regra "nasce pausado": campanha e conjunto pela
  Graph com `status=PAUSED`; anúncio pelo MCP só embaixo de conjunto pausado, publicado com
  `publish_as_active: false`. Rascunho não se apaga pela API: renomeie como `[APAGAR]`.
- **Editar conjunto que está no ar pode derrubá-lo para PAUSED.** Depois de qualquer edição em lote,
  confira o `effective_status` de cada item.
- **`PRIVACY_CHECK_FAIL` bloqueia mudança de status.** Resolva a causa, não fique insistindo.
- **Duas escritas em lote na mesma conta ao mesmo tempo** desalinham e a segunda toma rate limit.
  Uma subida por conta de cada vez. Contas diferentes podem ir em paralelo.
- **Duplicar campanha no Gerenciador deixa a cópia sem o robô do OneClick.** Recrie a otimização.

## API

- `GET /?ids=a,b,c` morreu na v26: consulte id a id.
- Leitura de insights: `since`/`until` soltos são ignorados. Use `time_range={"since":..,"until":..}`.
