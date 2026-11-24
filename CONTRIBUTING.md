# Como contribuir

Obrigado por querer ajudar. O kit é feito por gestor de tráfego para gestor de tráfego, e a melhor
contribuição costuma vir do dia a dia: um termo que deu reprovação no seu nicho, um erro da API que
você já resolveu, um instalador que quebrou na sua máquina.

## A regra de ouro

Nada que identifique cliente, conta ou pessoa entra no repositório. Isso vale para código, exemplo,
teste, print e mensagem de commit:

- dado de cliente (nome, faturamento, print de painel, conversa);
- ID de conta de anúncio, página, pixel ou Instagram de verdade. Em exemplo, use zeros: `act_000000000000000`;
- token de qualquer plataforma, chave de API, senha;
- telefone, e-mail ou ID de contato e de grupo do WhatsApp;
- caminho do seu computador, como /Users/seu-nome ou /home/seu-nome. Use `~/` ou caminho relativo.

O CI roda `testes/varredura.py` em todo PR e falha se achar caminho de usuário do Mac, ID de conta,
token da Meta ou ID do WhatsApp. Se a ocorrência for legítima (um filtro de SQL, por exemplo), ponha a
linha em `testes/varredura-permitidos.txt` e explique no PR.

Subiu um token sem querer? Revogue o token na plataforma primeiro. Apagar o commit não basta, porque o
histórico já foi publicado.

## Como rodar

Você precisa de `git`, `bash` e Python 3.9 ou mais novo. Cada ferramenta lista o que mais precisa no
README da pasta.

```bash
git clone https://github.com/MatheusSBPRO/kit-trafego-ia
cd kit-trafego-ia
./instalar.sh nome-da-ferramenta            # confere o ambiente, sem copiar nada
./instalar.sh --global nome-da-ferramenta   # instala em ~/.claude/skills (e ~/.codex/skills)
```

Servidor MCP direto do código, sem instalar:

```bash
PYTHONPATH=src python3 -m kit_trafego_ia --version
claude mcp add kit-trafego-dev -- env PYTHONPATH="$PWD/src" python3 -m kit_trafego_ia
```

O servidor não guarda cópia dos scripts: ele lê `ferramentas/subir-campanha-meta/.../meta_subir.py`
e `ferramentas/checar-criativo-meta/scripts/checar_criativo.py`. Quem muda o script muda o MCP junto.

## Como testar

Rode antes de abrir o PR. É o mesmo que o CI roda, em Python 3.9 e 3.12:

```bash
python3 -m py_compile $(git ls-files '*.py')   # todo .py compila
for f in $(git ls-files '*.sh'); do bash -n "$f"; done
python3 testes/varredura.py                    # nada sensível no repositório
python3 testes/testar_mcp.py                   # servidor MCP de ponta a ponta, sem token e sem rede
```

Para testar o pacote como ele vai para o PyPI:

```bash
uv build
python3 testes/testar_mcp.py uvx --from dist/kit_trafego_ia-*.whl kit-trafego-ia
```

Mexeu na lista de termos do `checar-criativo-meta`? Rode o script com uma frase que deve marcar e outra
que não deve, e cole as duas saídas no PR:

```bash
python3 ferramentas/checar-criativo-meta/scripts/checar_criativo.py --texto "frase que deve marcar"
```

Mexeu no `meta_subir.py`? Rode `--simular` com o `plano.exemplo.json` e cole a saída. Nunca teste
subida em conta de cliente: use uma conta sua, e tudo nasce pausado.

## Padrão de PR

- **Um assunto por PR.** Termo novo e conserto de instalador vão em PRs separados.
- **Título no imperativo, em português:** "Adiciona termos de saúde mental ao checar-criativo".
- **Diga como testou**, com o comando e a saída. O modelo de PR já traz a lista.
- **Texto em pt-BR com acento**, direto, sem emoji. Inglês é bem-vindo em tradução.
- **Só biblioteca padrão** no servidor MCP e nos scripts que ele usa. Dependência nova em outra
  ferramenta precisa estar no README e no `instalar.sh` dela.
- **Nada liga sozinho.** Mudança que permita criar campanha, conjunto ou anúncio ativo não entra.
- Antes de começar algo grande, abra uma issue para alinhar.

## Por onde começar

As issues marcadas como
[boa primeira issue](https://github.com/MatheusSBPRO/kit-trafego-ia/issues?q=is%3Aissue+is%3Aopen+label%3A%22boa+primeira+issue%22)
são pequenas e dizem onde mexer e como testar. As marcadas como
[ajuda bem-vinda](https://github.com/MatheusSBPRO/kit-trafego-ia/issues?q=is%3Aissue+is%3Aopen+label%3A%22ajuda+bem-vinda%22)
pedem um pouco mais de contexto. Comente na issue antes de começar, para ninguém fazer em dobro.

## Conduta

Participar aqui é concordar com o [Código de Conduta](CODE_OF_CONDUCT.md).
