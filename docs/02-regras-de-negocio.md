# Regras de negócio

## 1. Pedido e planilha

- Cada planilha aceita cria um pedido independente e imutável.
- Não existe versionamento da mesma planilha.
- Reimportação binariamente idêntica é duplicidade.
- Arquivos diferentes não são inferidos como versões entre si.
- Antes de qualquer NF aprovada, administrador pode remover importação errada e importar novamente; a remoção fica auditada.
- Depois de faturamento aprovado, pedido não pode ser substituído ou removido.
- Não existe encerramento manual de pedido com saldo.
- O pedido sai da lista ativa somente quando não possui saldo; continua nos relatórios.

### Linhas válidas

- quantidade vazia ou zero: ignorar;
- quantidade negativa: erro/revisão;
- títulos, totais e linhas decorativas: não criar item;
- preservar aba, linha e valor original para auditoria.

Preço da planilha é apenas estimativo. Não participa do match e não bloqueia aprovação.

Se a planilha não possui data, usar a data de importação como data operacional sem fingir que estava no original.

### Repetições

Linhas com mesmo código somente podem ser somadas para o match quando código, produto, unidade, tamanho, preço estimado preenchido e demais condições relevantes forem equivalentes. Originais permanecem separados. Diferença gera alerta e impede consolidação automática.

### Unidades

Separar:

- quantidade de embalagens;
- unidade comercial (`UN`, `CX`, `BD`, `GL` etc.);
- tamanho/conteúdo (`18 L`, `3,6 L`, `25 kg` etc.).

Conversões dependem de regra explícita por produto, fornecedor ou modelo. Nunca presumir equivalência entre peso e volume.

## 2. NF-e

- Somente NF-e modelo 55 é processada no MVP.
- XML autorizado é obrigatório e fiscalmente oficial.
- PDF é opcional e apenas visual.
- Chave de acesso identifica unicamente a NF dentro da empresa.
- XML, cabeçalho e itens fiscais são imutáveis.
- Normalizações e associações ficam separadas dos dados originais.
- XML nunca é excluído automaticamente e permanece consultável e baixável.

Bonificação, brinde e remessa são registrados e relatados, mas não consomem saldo. Devolução fica em relatório próprio e não recalcula pedido automaticamente no MVP. Classificação insegura exige revisão.

NF cancelada não pode faturar. Cancelamento posterior confirmado invalida alocações, devolve quantidades ao saldo e preserva todo o histórico. Eventos fiscais automáticos ficam no roadmap; no MVP a ação exige evidência e administrador.

## 3. Produtos e aliases

- Produto é cadastrado por fornecedor; não unificar fornecedores diferentes no MVP.
- Código normalizado do fornecedor é evidência principal.
- Alias confirmado vale para todas as lojas da mesma empresa.
- Um alias ativo não pode apontar para dois produtos do mesmo fornecedor.
- EAN é evidência complementar.
- Similaridade textual sem código cria sugestão, não match confirmado.
- Confirmação administrativa pode criar alias auditado e recalcular a conferência.

Código e quantidade compatíveis prevalecem sobre diferença de descrição. A diferença pode ser mostrada para revisão cadastral sem reduzir automaticamente o match.

## 4. Candidatas e associação

Filtrar candidatas por:

1. empresa;
2. loja/CNPJ destinatário;
3. fornecedor/CNPJ emitente;
4. pedido aberto ou parcialmente faturado;
5. existência de saldo;
6. ausência de conflito com associação vigente da mesma NF.

Loja desconhecida ou ausência de planilha candidata deixa a NF válida na Fila, não no Diagnóstico.

Uma NF possui no máximo uma associação vigente. Um pedido pode receber muitas NFs.

### Quantidades

- NF igual ao saldo: match integral;
- NF menor que o saldo do mesmo item: cabe integralmente, mas gera alerta de parcialidade da linha;
- item do pedido ausente na NF: permanece em saldo e não reduz a cobertura da NF;
- NF maior que o saldo: não alocar antes da aprovação; exibir excesso;
- item da NF ausente no pedido: extra, sem alocação automática.

Após aprovação excepcional de excesso, alocar no máximo o saldo; excesso permanece divergência e saldo nunca fica negativo.

### Dois tipos de parcialidade

- **Pedido parcial por itens:** alguns produtos faturados integralmente e outros continuam em saldo. É normal.
- **Linha parcial em quantidade:** saldo 10 e NF 6. É raro e gera alerta.

## 5. Compatibilidade

`cobertura de itens = linhas confirmadas da NF / linhas relevantes da NF`

Sugestão textual não confirmada não conta como item confirmado.

Cobertura de quantidade é a média, por linha confirmada, da parcela da quantidade da NF que cabe no saldo. Não somar unidades heterogêneas de produtos diferentes.

`compatibilidade = mínimo(cobertura de itens, cobertura de quantidades)`

| Resultado | Nível |
| --- | --- |
| 100% | Alta |
| 85% a 99,99% | Média |
| abaixo de 85% | Baixa |

Alertas são independentes do percentual. É possível `100% — ALTA — COM ALERTA`.

Empate apresenta o pedido mais antigo primeiro, mas mantém associação ambígua e exige escolha administrativa. `xPed`, `nItemPed`, data e histórico são complementares e nunca superam conflitos críticos.

## 6. Decisão administrativa

- Não existe aprovação automática.
- Aprovação e reprovação são da NF/conferência inteira, não item a item.
- Somente Administrador ou Mestre decide.
- Divergência exige explicação simples e objetiva.
- Troca manual de planilha recalcula tudo e exige justificativa.
- Aprovação cria associação e alocações em transação com nova validação dos saldos.
- A cópia preenchida gerada após aprovação é uma saída operacional da planilha do pedido, com colunas de faturamento por item alocado: quantidade faturada, número da NF, série, data de faturamento e valor total da NF.
- O nome exibido e baixado da cópia preenchida deve identificar a planilha original, a NF, a série e a loja, sem depender apenas de identificador técnico.
- Concorrência ou mudança de saldo bloqueia e recalcula.
- Reprovação não apaga a NF; remove-a da Fila e registra relatório/histórico.
- Anulação invalida as alocações e restaura saldos sem apagar eventos.

## 7. Estados e saldos

Cada item mantém quantidades:

- `SALDO`;
- `FATURADO` ainda não recebido;
- `RECEBIDO`.

Invariante:

`pedido = saldo + faturado + recebido`

Estado do pedido:

| Estado | Regra |
| --- | --- |
| `ABERTA` | tudo em saldo |
| `PARCIALMENTE_FATURADA` | existe saldo e também faturado ou recebido |
| `FATURADA` | sem saldo e há material aguardando recebimento |
| `PARCIALMENTE_RECEBIDA` | sem saldo, parte faturada e parte recebida |
| `CONCLUIDA` | tudo recebido |

Não existe `CANCELADA` como encerramento comum de planilha. Importação errada sem faturamento pode ser removida por fluxo controlado.

## 8. Recebimento

- Importar NF significa faturamento, não chegada física.
- Somente Administrador ou Mestre confirma.
- Localizar principalmente por número da NF e fornecedor.
- Confirmar a NF inteira; não existe recebimento parcial no MVP.
- Informar data real manualmente; sistema audita usuário e momento do registro.
- Resultado: `RECEBIDA_SEM_DIVERGENCIA` ou `RECEBIDA_COM_DIVERGENCIA`.
- Divergência exige ocorrência vinculada à NF inteira.
- Ocorrência registra tipo e descrição; pode mencionar itens e quantidades em texto.
- Sem fotos ou anexos no MVP.
- Divergência não desfaz o recebimento e fica destacada até resolução.
- Anulação de recebimento é exclusiva de administrador e preserva o evento anterior.
- 30 dias desde emissão/faturamento sem recebimento gera alerta administrativo informativo, sem bloqueio ou justificativa.

## 9. Arquivos e retenção

- XML: permanente, imutável, consultável e baixável.
- Planilha original: preservada enquanto o pedido estiver ativo; após faturamento total, pode entrar em rotina controlada de retenção/descarte, desde que banco, auditoria e cópia preenchida estejam íntegros e exista backup conforme política aprovada.
- Cópia preenchida: preservada como saída de backup; nunca é fonte operacional de verdade.
- PDF: apoio opcional, sujeito à política configurada.
- Nenhum arquivo é removido apenas da pasta de origem para representar processamento.
- Toda eliminação permitida registra hash, usuário, data e motivo.

## 10. Diagnóstico versus Fila

Fila: NF válida com divergência de negócio, baixa compatibilidade, ambiguidade, loja desconhecida ou sem planilha.

Diagnóstico: XML/planilha ilegível, estrutura não reconhecida, erro de extração, processamento interrompido, inconsistência técnica, falha de saída ou possível duplicidade divergente.

Resolvido sai da lista ativa e permanece no relatório.
