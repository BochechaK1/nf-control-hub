# Relatorio de situacao - NF Control Hub

Data: 12/08/2026  
Branch atual: `ajuste-reconhecimento-planilhas`  
Ultimo commit enviado: `dcd669d Melhora reconhecimento de planilhas e exportacoes`

## Resumo executivo

O projeto esta em fase de MVP funcional local, com fluxo principal ja operando: importacao de planilhas de pedido, importacao de XML NF-e, identificacao de loja e fornecedor, calculo de conferencia, aprovacao administrativa, alocacao de saldo, exportacao de copia preenchida, relatorios, recebimento e diagnostico.

O sistema ja processa fornecedores diferentes e nao depende mais de Coral como regra fixa. O reconhecimento de fornecedor/planilha foi tornado conservador para evitar associacao incorreta, e a recuperacao de planilhas pode usar evidencias de loja, nome distintivo do fornecedor e coincidencia de codigos de itens.

## Estado do repositorio

- Repositorio remoto: `https://github.com/BochechaK1/nf-control-hub.git`
- Branch de trabalho: `ajuste-reconhecimento-planilhas`
- Branch local acompanha: `origin/ajuste-reconhecimento-planilhas`
- Ultimo commit remoto: `dcd669d`
- Existem alteracoes locais ainda nao commitadas apos o ultimo push.

Arquivos alterados localmente no momento deste relatorio:

- `docs/relatorio-situacao-2026-08-12.md`
- `docs/02-regras-de-negocio.md`
- `reports/services.py`
- `reports/tests.py`
- `templates/ui/fila.html`
- `ui/tests.py`
- `ui/views.py`

Essas alteracoes tratam principalmente de:

- exibicao da planilha e loja usadas na Fila, em vez de UUID do pedido;
- uso da candidata aprovada como fotografia da NF aprovada;
- novo formato da copia preenchida com cabecalho operacional;
- testes de regressao desses comportamentos.

## Funcionalidades implementadas

### Importacao de planilhas

- Importa planilhas Excel de layouts diferentes.
- Detecta cabecalhos equivalentes, como codigo, produto/descricao e quantidade.
- Ignora linhas vazias, totais, quantidade zero e linhas decorativas.
- Envia planilhas invalidas para Diagnostico, sem derrubar a aplicacao.
- Preserva valores originais e valores normalizados.
- Evita associar automaticamente planilha a fornecedor unico quando o nome do arquivo indica outro fornecedor.
- Reprocessa planilhas armazenadas que antes ficaram sem pedido quando passa a existir evidencia suficiente.

### Importacao de XML NF-e

- Processa XML NF-e modelo 55 autorizado.
- Usa o XML como fonte fiscal principal e imutavel.
- Identifica fornecedor pelo CNPJ do emitente.
- Identifica loja pelo CNPJ do destinatario.
- Registra fornecedor automaticamente quando aparece no XML.
- Detecta XML duplicado por hash/chave.
- Mantem NF valida na Fila quando falta loja ou planilha candidata, em vez de enviar para Diagnostico.

### Matching e Fila

- Compara NF contra pedidos por empresa, loja, fornecedor, status aberto/parcial e saldo.
- Usa codigo normalizado como evidencia principal.
- Similaridade textual sem codigo vira sugestao, nao match automatico.
- Itens do pedido que nao vieram na NF permanecem como saldo e nao derrubam a compatibilidade da NF.
- NF com item extra gera alerta.
- NF menor que saldo do item gera alerta de parcialidade de linha.
- NF aprovada agora mostra a candidata aprovada da associacao, nao uma conferencia recalculada posteriormente com saldo zero.
- A Fila mostra a planilha usada e a loja de forma legivel, por exemplo `CORAL PARATY 001.xlsx - paraty`, em vez de exibir apenas UUID.

### Aprovacao e saldo

- Aprovacao exige Administrador ou Mestre.
- Nenhuma aprovacao e feita automaticamente.
- Divergencia exige justificativa.
- Aprovacao cria Associacao e Alocacoes em transacao.
- O saldo dos itens e atualizado sem permitir saldo negativo.
- Anulacao restaura saldos e preserva historico.

### Exportacao de copia preenchida

- Apos aprovacao, o sistema gera uma copia preenchida operacional da planilha.
- A planilha original nao e alterada.
- As colunas de faturamento entram no cabecalho original da planilha.
- Cabecalho atual da saida:
  - `quantidade faturada`
  - `numero da nota`
  - `valor da nota`
  - `data do faturamento`
- O nome do arquivo baixavel identifica planilha original, NF, serie e loja.
- A listagem de Exportacoes mostra planilha original, NF e loja para facilitar identificacao.

### Relatorios, recebimento e diagnostico

- Relatorios mostram alocacoes, exportacoes, historico e notas recentes.
- Recebimento permite confirmar NF inteira, com ou sem divergencia.
- Diagnostico separa falhas tecnicas de problemas de negocio da Fila.
- Eventos relevantes sao auditaveis.

## Situacao do banco local de preview

Levantamento feito no banco local em 12/08/2026:

- Empresas: 1
- Lojas: 5
- Fornecedores: 3
- Usuarios: 1
- Arquivos totais: 48
- Planilhas de pedido: 9
- XMLs NF-e: 8
- PDFs/DANFE: 0
- Exportacoes: 31
- Pedidos ativos: 8
- Itens de pedido: 528
- NFs importadas: 8
- NFs aguardando aprovacao: 0
- NFs aprovadas: 8
- NFs rejeitadas: 0
- NFs anuladas: 0
- Associacoes vigentes: 8
- Alocacoes vigentes: 492
- Recebimentos vigentes: 1
- Diagnosticos abertos: 0
- Tarefas em erro: 0

CNPJs atuais das lojas:

- `matriz`: `09.580.958/0001-73`
- `centro`: `09.580.958/0003-35`
- `paraty`: `09.580.958/0002-54`
- `japuiba`: `18.207.331/0001-62`
- `bracui`: `09.580.958/0004-16`

## Validacoes recentes

Ultimas validacoes executadas durante os ajustes:

```powershell
$env:NFCH_ALLOW_SQLITE_TESTS='true'
py manage.py check --settings=nf_control_hub.settings.test
py manage.py test --settings=nf_control_hub.settings.test
```

Resultado conhecido mais recente: `66 tests`, todos OK.

Tambem foram executados testes focados:

```powershell
py manage.py test reports --settings=nf_control_hub.settings.test
py manage.py test ui --settings=nf_control_hub.settings.test
```

Resultados: OK.

## Riscos e pontos de atencao

- O ambiente local usa SQLite de preview. Ele e util para desenvolvimento, mas pode travar com escritas concorrentes. O MVP final deve usar PostgreSQL, conforme escopo.
- A Fila nao deve escrever no banco durante carregamento de pagina. Esse problema ja foi corrigido, mas deve continuar sendo um criterio de regressao.
- O motor de match ainda depende de codigo de produto normalizado. Casos sem codigo confiavel exigem sugestao ou alias confirmado.
- A recuperacao de planilhas por coincidencia de codigo deve permanecer conservadora para evitar vinculo com fornecedor errado.
- Exportacoes antigas continuam preservadas no historico; as novas copias usam a observacao/versao mais recente.
- Ainda nao ha tela administrativa propria para corrigir cadastro de lojas/fornecedores dentro da UI; ajustes foram feitos por comando/shell no preview.
- Ainda nao ha worker separado real com fila persistente operando fora do request, embora o modelo de tarefas exista.

## Pendencias recomendadas

1. Criar tela administrativa interna para cadastro/correcao de lojas, CNPJs e fornecedores.
2. Criar fluxo controlado para remover importacao errada antes de faturamento, com auditoria pela UI.
3. Criar botao/acao explicita para gerar ou regenerar copia preenchida, sem escrita em GET.
4. Melhorar visualizacao da planilha usada na Fila e Relatorios com filtros por loja, fornecedor e status.
5. Migrar o ambiente de preview operacional para PostgreSQL antes de uso com mais usuarios.
6. Implementar worker separado para processamento de arquivos e reprocessamento da fila.
7. Criar rotina de backup/restauracao documentada para banco e storage.
8. Expandir fixtures reais controladas por fornecedor, sem versionar XML fiscal ou planilha sensivel no GitHub.

## Proximo passo sugerido

Antes de novo push, commitar as alteracoes locais atuais em uma nova mensagem focada, por exemplo:

```text
Aprimora exibicao da fila e formato da copia preenchida
```

Descricao sugerida:

```text
Mostra planilha e loja utilizadas na Fila, preserva a fotografia da candidata aprovada para NFs ja associadas e ajusta a copia preenchida para usar o cabecalho operacional solicitado.
```
