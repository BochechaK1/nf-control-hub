# Modelo de dados

## Princípio

O estado vigente é produzido por registros históricos, associações e alocações. Não sobrescrever eventos para simular o presente.

## Entidades

### Organização e acesso

- `EmpresaCliente`
- `Loja`
- `Usuario`
- `UsuarioLoja`
- `Fornecedor`
- `FornecedorAlias`

### Produtos

- `ProdutoFornecedor`
- `ProdutoFornecedorAlias`

### Pedidos

- `Pedido`
- `ItemPedido`
- `ModeloPlanilha`
- `ModeloPlanilhaVersao`

O modelo do fornecedor pode ter versões; o pedido importado não.

### Fiscal e conferência

- `NotaFiscal`
- `ItemNotaFiscal`
- `Conferencia`
- `ConferenciaCandidata`
- `ConferenciaItem`
- `Associacao`
- `Alocacao`

### Operação e suporte

- `Recebimento`
- `OcorrenciaRecebimento`
- `Arquivo`
- `TarefaProcessamento`
- `Diagnostico`
- `EventoAuditoria`
- `Exportacao`

## Relações essenciais

- Empresa possui lojas, usuários e fornecedores.
- Usuário pode acessar uma ou várias lojas.
- Fornecedor atende várias lojas.
- Pedido pertence a uma loja e fornecedor e possui muitos itens.
- NF pertence a emitente e destinatário fiscal e possui muitos itens.
- NF pode ter muitas conferências históricas, mas uma associação vigente.
- Associação vigente aponta para exatamente um pedido.
- Alocação liga item da NF a item do pedido e registra quantidade.
- Recebimento pertence à NF inteira.
- Ocorrência pertence ao recebimento/NF inteira, não ao item.
- Arquivo pode pertencer a pedido, NF, diagnóstico ou exportação.

## Identidades e unicidade

- toda entidade de negócio contém `empresa_cliente_id`;
- loja: identificador interno imutável e código único dentro da empresa;
- CNPJ é identificador fiscal principal, mas não chave técnica;
- NF: chave de acesso única dentro da empresa;
- pedido: UUID/ID interno; nome do arquivo não é identidade;
- arquivo: hash criptográfico e ID; caminho não é identidade;
- alias de produto: único por empresa + fornecedor + tipo + valor normalizado.

Se duas lojas compartilham CNPJ, usar evidências adicionais e revisão; nunca escolher silenciosamente.

## Imutabilidade

Imutáveis:

- XML e dados fiscais extraídos;
- pedido e linhas originais após aceitação;
- eventos de auditoria;
- decisões e eventos históricos.

Anuláveis, não apagáveis:

- associação;
- alocação;
- aprovação;
- recebimento.

Desativáveis:

- empresa;
- loja;
- fornecedor;
- usuário;
- alias;
- modelo de planilha.

## Alocação e saldo

`saldo oficial = quantidade pedida - soma(alocações aprovadas vigentes)`

Restrições:

- quantidade alocada > 0;
- soma por item do pedido <= quantidade pedida;
- soma por item da NF <= quantidade fiscal;
- no máximo uma associação vigente por NF;
- aprovação/anulação usa transação e bloqueio das linhas envolvidas.

`ItemPedido` pode guardar cache de saldo, faturado e recebido para telas. Cache:

- não é fonte de verdade;
- atualiza na mesma transação;
- pode ser reconstruído;
- é conferido periodicamente;
- divergência gera Diagnóstico.

## Estados separados da NF

Não usar um único status para tudo.

| Dimensão | Exemplos |
| --- | --- |
| Fiscal | `FATURADA`, `CANCELADA` |
| Conferência | `AGUARDANDO_APROVACAO`, `APROVADA`, `REJEITADA`, `ANULADA` |
| Recebimento | `AGUARDANDO_RECEBIMENTO`, `RECEBIDA_SEM_DIVERGENCIA`, `RECEBIDA_COM_DIVERGENCIA` |

Uma NF pode estar fiscalmente cancelada, ter associação anulada e conservar recebimento físico histórico.

## Arquivo

Campos mínimos:

- empresa;
- tipo/finalidade;
- nome original;
- MIME type;
- tamanho;
- hash;
- localização controlada;
- usuário e momento da importação;
- vínculo de negócio;
- situação;
- política de retenção.

Conteúdo fica no armazenamento controlado; metadados e vínculos ficam no PostgreSQL.

## Auditoria

Append-only, contendo:

- empresa;
- usuário/processo;
- sessão e origem quando aplicável;
- entidade e ID;
- ação;
- data/hora;
- antes/depois permitido;
- motivo/justificativa.

Sem exclusão em cascata de referências históricas.

