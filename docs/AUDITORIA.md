# Auditoria do Documento Mestre

## Resultado

O conteúdo funcional estava rico, mas o formato acumulativo continha decisões antigas ao lado das decisões atuais. Isso criaria risco real de o Codex implementar uma regra já substituída.

O novo pacote separa instruções, produto, regras, dados, arquitetura, plano, testes e roadmap. Os arquivos numerados passam a ser autoritativos; o Documento Mestre v0.1 fica histórico.

## Contradições e duplicidades resolvidas

| Tema | Problema encontrado | Regra consolidada |
| --- | --- | --- |
| Histórico | Aparecia como item do menu e depois era movido | Histórico fica dentro de Relatórios |
| Itens faturados | Existia no menu original | Fica como relatório consultivo |
| Inventário | Aparecia como módulo e depois foi adiado | Fora do MVP; roadmap anual |
| Perfis | Trechos falavam só em Admin/Viewer | Mestre é papel interno; clientes usam Admin/Viewer |
| Aprovação | Status antigos misturavam fiscal, conferência e recebimento | Três dimensões de estado separadas |
| Pedido cancelado | Status `CANCELADA` conflitava com ausência de encerramento com saldo | Sem cancelamento comum; importação errada pré-aprovação pode ser removida |
| Versões de planilha | Houve proposta de versionamento e posterior rejeição | Cada arquivo aceito é pedido independente e imutável |
| Faturamento parcial | “Parcial” misturava itens omitidos e quantidade menor | Pedido parcial por itens é normal; linha parcial gera alerta |
| Compatibilidade | Percentual aparecia sem fórmula definitiva | Mínimo entre cobertura de itens e de quantidades |
| Descrição | Em alguns trechos poderia sugerir associação forte | Sem código, descrição gera apenas sugestão |
| Ocorrência | Havia vínculo opcional com item | Ocorrência pertence à NF inteira |
| Recebimento | Trechos antigos pediam responsável físico | Registrar data real e administrador da operação; sem campo de recebedor físico |
| Retenção | “Preservar todos” e “descartar após faturamento” coexistiam | XML permanente; planilha/PDF seguem política controlada; cópia e banco preservam resultado |
| Infraestrutura | Arquitetura futura aparecia próxima do MVP | Windows interno agora; Docker/Linux/nuvem no roadmap |
| Acesso | Web externo era cogitado | MVP somente na rede já conectada ao servidor |
| Dashboard | Dashboard avançado fora do MVP, mas Dashboard básico definido | Dashboard básico por perfil no MVP; análises avançadas no roadmap |
| Decisões pendentes | Lista antiga continha questões já respondidas | Removida da instrução ativa; pendências reais listadas abaixo |

## Regras preservadas como centrais

- XML fonte fiscal, imutável e permanente.
- Uma NF para uma planilha; uma planilha para várias NFs.
- Aprovação completa e administrativa.
- Saldo derivado de alocações vigentes.
- Estados Saldo, Faturado e Recebido.
- Match centrado no conteúdo da NF, não na cobertura total do pedido.
- Divergência explicável e associação manual auditada.
- Banco como fonte operacional; planilha preenchida como saída.

## Pendências reais que não bloqueiam o primeiro marco

- destino definitivo e retenção temporal dos backups;
- política exata de descarte da planilha original e PDF depois do faturamento total;
- volume mensal real e limites de upload;
- confirmação da conectividade de Bracuí;
- modelos e casos dourados dos fornecedores além da Coral;
- limiar de recontagem do futuro Inventário;
- grafia comercial definitiva de `Destiny In`.

Até decisão, aplicar a opção conservadora: não eliminar arquivo, limitar upload por configuração segura e não incluir loja sem conectividade comprovada.

## Recomendações de manutenção

- Não voltar a acrescentar seções indefinidamente ao Documento Mestre histórico.
- Alterar somente o arquivo temático correspondente.
- Toda mudança de regra deve incluir caso de teste.
- `AGENTS.md` deve permanecer curto; detalhes ficam em `docs/`.
- Revisar links e contradições antes de cada marco de implantação.

