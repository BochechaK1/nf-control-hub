# Plano de desenvolvimento

## Estratégia

Desenvolvimento solo por Kauan com Codex. Construir primeiro uma fatia vertical completa usando o caso Coral/Matriz. Não desenvolver todas as telas superficialmente.

Novas ideias vão para backlog. Apenas requisito bloqueante, correção ou tarefa da fase atual pode interromper o plano.

## Fase A — Piloto Coral

### A1. Fundação

- repositório novo;
- Django e PostgreSQL;
- configurações de desenvolvimento/teste/servidor;
- Empresa, Loja, Usuário e login;
- testes iniciais;
- estrutura de auditoria.

Gate: navegador abre, administrador autentica, banco conecta e testes passam.

### A2. Pedidos

- Arquivo, hash e duplicidade;
- upload múltiplo;
- Pedido e ItemPedido;
- adaptador Coral;
- linhas válidas, códigos, quantidades e unidades;
- tela básica de pedido e saldo inicial.

Gate: planilha Coral real produz exatamente os itens esperados.

### A3. NF-e

- parser de modelo 55;
- NotaFiscal e ItemNotaFiscal;
- fornecedor automático;
- loja por CNPJ;
- chave única;
- armazenamento permanente do XML.

Gate: XML Coral real é extraído sem alteração fiscal e sem duplicação.

### A4. Match e Fila

- candidatas;
- normalização;
- match código/quantidade;
- coberturas e alertas;
- detalhe item a item;
- alternativas e seleção manual.

Gate: caso Coral aponta a planilha correta e reproduz divergências conhecidas.

### A5. Aprovação e saldo

- Conferencia, Associação e Alocação;
- aprovação/reprovação;
- justificativas;
- transações e concorrência;
- anulação e recálculo;
- várias NFs por pedido.

Gate: aprovar e anular restaura exatamente os saldos.

### A6. Saída e instalação

- cópia preenchida;
- download e histórico mínimo;
- serviços Windows;
- backup/restauração;
- acesso interno;
- health check.

Gate: fluxo Coral completo funciona após reinício e restauração testada.

Estimativa conservadora já com Codex: 12 a 20 dias efetivos de trabalho focado, não necessariamente corridos.

## Fase B — MVP interno

1. novos fornecedores e modelos versionados;
2. aliases confirmados;
3. Visualizador e escopo por loja;
4. recebimento integral e ocorrências;
5. Diagnóstico e reprocessamento;
6. Relatórios, Histórico e exportações;
7. Dashboard por perfil;
8. Configurações completas;
9. fila e lotes otimizados;
10. atualização central segura.

Cada fornecedor exige pelo menos uma planilha, um XML e resultado esperado documentado.

## Padrão de tarefa para o Codex

```text
Objetivo: implementar [uma unidade específica].

Regras: seguir AGENTS.md e as seções [X] da documentação.

Escopo: alterar somente [módulos].

Critérios de aceite:
- [resultado verificável]
- [teste obrigatório]

Antes de alterar, inspecione o código existente.
Implemente, execute os testes e informe arquivos modificados,
resultados, riscos e validação manual.
```

## Definition of Done

- regra confirmada;
- migração correta, quando aplicável;
- testes unitários e de integração passando;
- arquivo real validado, quando aplicável;
- sem regressão nos casos dourados;
- permissões e auditoria verificadas;
- documentação consistente;
- instruções de validação entregues.

