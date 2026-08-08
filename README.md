# NF Control Hub

Aplicacao web interna em Django para importar planilhas de pedidos e XMLs de NF-e, conferir itens e quantidades, aprovar associacoes, acompanhar saldos, recebimento e relatorios auditaveis.

Criado por Kauan Gomes / Destiny In.

## Estrutura

```text
accounts/          usuarios, perfis e escopo por loja
approvals/         aprovacao, associacao e alocacoes
audit/             eventos auditaveis
diagnostics/       diagnosticos tecnicos e tarefas
files/             armazenamento e controle de arquivos
invoices/          NF-e e itens fiscais
matching/          motor de conferencia e candidatas
orders/            pedidos e itens importados de planilhas
organizations/     empresas, lojas e fornecedores
receiving/         recebimento e ocorrencias
reports/           exportacoes e relatorios
ui/                views da interface interna
templates/ui/      templates Django
static/ui/         CSS e JS do frontend
samples/           arquivos de exemplo sem dados sensiveis
docs/              especificacao do produto e regras do MVP
```

Arquivos locais como banco SQLite de preview, uploads fiscais, exportacoes e caches ficam fora do Git pelo `.gitignore`.

## Requisitos

- Python 3.12+ recomendado
- PostgreSQL para uso real
- Windows Server ou Windows local para o MVP

Dependencias Python:

```powershell
py -m pip install -r requirements.txt
```

## Configuracao

Crie um `.env` a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Ajuste no `.env`:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_*`
- `NFCH_STORAGE_ROOT`
- `NFCH_TEMP_ROOT`

## Rodar em preview local

Para abrir localmente sem PostgreSQL, use o modo de teste com SQLite:

```powershell
$env:NFCH_ALLOW_SQLITE_TESTS='true'
py manage.py migrate --settings=nf_control_hub.settings.test
py manage.py runserver --settings=nf_control_hub.settings.test 127.0.0.1:8000
```

Acesse:

```text
http://127.0.0.1:8000/
```

## Testes

```powershell
$env:NFCH_ALLOW_SQLITE_TESTS='true'
py manage.py test --settings=nf_control_hub.settings.test
```

## Documentacao

Leia a especificacao em ordem:

1. [AGENTS.md](AGENTS.md)
2. [docs/01-produto-e-escopo.md](docs/01-produto-e-escopo.md)
3. [docs/02-regras-de-negocio.md](docs/02-regras-de-negocio.md)
4. [docs/03-modelo-de-dados.md](docs/03-modelo-de-dados.md)
5. [docs/04-arquitetura-mvp.md](docs/04-arquitetura-mvp.md)
6. [docs/05-plano-de-desenvolvimento.md](docs/05-plano-de-desenvolvimento.md)
7. [docs/06-casos-de-teste.md](docs/06-casos-de-teste.md)
8. [docs/07-roadmap.md](docs/07-roadmap.md)
9. [docs/AUDITORIA.md](docs/AUDITORIA.md)

Para publicar, siga [docs/GITHUB.md](docs/GITHUB.md).

## Importante

- XML fiscal e arquivos operacionais nao devem ser enviados ao GitHub.
- `.env` nunca deve ser versionado.
- `local_preview.sqlite3` e `storage/` sao apenas dados locais.
- O fluxo de aprovacao nunca aprova automaticamente; sempre exige usuario autorizado.
