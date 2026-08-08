# Casos de teste e critérios de aceite

## Estratégia

- unitários: normalização, estados, métricas e fórmulas;
- banco: restrições, transações, concorrência e escopo;
- integração: Excel, XML, arquivos e exportação;
- ponta a ponta: importação até recebimento;
- regressão: casos reais controlados.

Nunca usar somente mocks para validar parser de Excel/XML.

## Caso dourado CT-001 — Coral/Matriz

Arquivos de referência já analisados:

- `MATRIZ (2).xlsx`;
- XML da NF-e 1.987.853;
- PDF correspondente como apoio.

Expectativas registradas:

- somente linhas com quantidade preenchida representam pedido no modelo Coral;
- `CODIGO DO ITEM` é chave principal do modelo;
- `cProd` deve normalizar zeros à esquerda sem alterar original;
- EAN da amostra não é confiável para match automático;
- 48 itens na NF;
- 36 linhas da planilha encontradas;
- 12 itens extras/não encontrados;
- 4 itens do pedido ausentes da NF, totalizando 47 unidades em saldo;
- 2 itens excedem o pedido, totalizando 16 unidades;
- pedido `W000062885` aparece no XML/DANFE;
- eventual aprovação deixa o pedido `PARCIALMENTE_FATURADA`.

O relatório detalhado `NF_Control_Hub_Caso_Teste_Coral_001.md` permanece como anexo de evidência. Antes do uso como fixture automatizada, revisar se dados fiscais precisam ser protegidos no repositório.

## Casos obrigatórios do motor

### CT-002 — Pedido parcialmente faturado por itens

Pedido: X=10, Y=3. NF: X=10.

Esperado:

- X passa a faturado após aprovação;
- Y permanece saldo 3;
- cobertura da NF pode ser 100%;
- pedido fica parcialmente faturado;
- nova NF Y=3 encontra o mesmo pedido.

### CT-003 — Parcialidade da linha

Saldo X=10. NF X=6.

Esperado:

- cobertura quantitativa da NF para a linha é 100%;
- alerta de quantidade parcial obrigatório;
- após aprovação: saldo 4, faturado 6.

### CT-004 — Excesso

Saldo X=10. NF X=12.

Esperado:

- cobertura quantitativa da linha 83,33%;
- excesso 2;
- nenhuma alocação antes da aprovação;
- eventual aprovação aloca no máximo 10;
- saldo nunca negativo.

### CT-005 — Descrição diferente

Código e quantidade iguais, descrição diferente.

Esperado: match confirmado; descrição apenas informativa.

### CT-006 — Somente descrição semelhante

Sem código/alias, descrição semelhante.

Esperado: sugestão; não conta como match até confirmação administrativa.

### CT-007 — Empate

Duas candidatas com mesmos itens e quantidades.

Esperado: mais antiga aparece primeiro, associação marcada ambígua e nenhuma decisão automática.

### CT-008 — Concorrência

Duas aprovações tentam consumir o mesmo saldo.

Esperado: uma transação conclui; outra bloqueia/recalcula; nunca excede pedido.

### CT-009 — Anulação

Após aprovação, anular associação.

Esperado: alocações deixam de vigorar, saldo é recomposto, histórico permanece.

## Arquivos e fiscal

### CT-010 — XML duplicado

Mesmo hash e chave: uma NF ativa, segunda tentativa auditada.

### CT-011 — Mesma chave, conteúdo divergente

Esperado: Diagnóstico; nenhum descarte automático.

### CT-012 — Documento não suportado

NFC-e/CT-e: Diagnóstico, sem NF de pedido.

### CT-013 — Loja desconhecida

NF-e válida com CNPJ não cadastrado: Fila para revisão, não Diagnóstico.

### CT-014 — Cancelamento posterior

Esperado: associação anulada por evento, saldo recomposto, fiscal cancelada, recebimento histórico preservado com alerta.

## Recebimento

### CT-015 — Sem divergência

Confirmação integral com data real: todas as quantidades da NF passam de faturado para recebido.

### CT-016 — Com divergência

Exige ocorrência da NF; status recebido com divergência; destaque até resolução.

### CT-017 — Alerta 30 dias

NF aguardando recebimento há 30 dias: alerta apenas administrativo, sem bloqueio.

## Permissões

### CT-018 — Visualizador por loja

Não lista, abre, baixa ou exporta dados de loja não vinculada, inclusive por URL direta.

### CT-019 — Ações administrativas

Visualizador não aprova, reprova, anula, recebe, configura ou acessa Diagnóstico.

## Backup e operação

### CT-020 — Reinício

Tarefa aguardando continua; tarefa abandonada pode ser recuperada sem duplicar resultado.

### CT-021 — Restauração

Restaurar banco e arquivos recupera vínculos e hashes; XML continua baixável.

## Aceite de fornecedor novo

Nenhum novo modelo entra sem:

- planilha real controlada;
- XML real controlado;
- contagem esperada de itens;
- regras de código/unidade;
- divergências esperadas;
- teste de regressão automatizado.

