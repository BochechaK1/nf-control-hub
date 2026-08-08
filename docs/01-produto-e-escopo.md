# Produto e escopo do MVP

## Visão

NF Control Hub é uma aplicação web interna para importar planilhas de pedidos e NF-e, conferir itens e quantidades, submeter a associação à aprovação administrativa, acompanhar saldos, faturamento e recebimento e produzir histórico e relatórios auditáveis.

Criado por Kauan Gomes, Destiny In. Contato: `kauanalves.gomes14@gmail.com`.

O produto é independente da identidade da Cores de Angra e deve permitir implantação futura em outras empresas.

## Ambiente inicial

- uma instalação e um banco separados por cliente;
- servidor Windows existente;
- acesso somente pela rede interna que já alcança o servidor;
- 5 a 8 usuários simultâneos inicialmente;
- nenhuma exposição direta à internet;
- lojas sem rota interna ficam fora da primeira implantação.

Todas as entidades já devem pertencer a uma `EmpresaCliente` para facilitar futura evolução multiempresa.

## Perfis

| Perfil | Escopo |
| --- | --- |
| `MESTRE` | Kauan; acesso interno da plataforma a todas as empresas e lojas autorizadas |
| `ADMINISTRADOR` | Administração completa dentro da empresa cliente |
| `VISUALIZADOR` | Consulta somente das lojas vinculadas |

O papel Mestre não pode ser concedido por administradores comuns. Restrições devem existir no backend e também valer para filtros, detalhes, downloads e exportações.

## Menu do MVP

- Dashboard
- Fila
- Recebimento
- Planilhas
- Relatórios
- Diagnóstico — apenas administradores
- Configurações — apenas administradores
- Sobre

`Histórico` não é item independente: é uma categoria dentro de Relatórios. `Itens faturados` também fica dentro de Relatórios. `Inventário` não aparece no MVP.

## Entradas

- múltiplas planilhas Excel de fornecedores e estruturas diferentes;
- múltiplos XMLs de NF-e modelo 55;
- PDFs/DANFEs opcionais como apoio;
- importação manual pelo seletor de arquivos do navegador.

O histórico não depende de arquivos permanecerem na pasta de origem do usuário.

## Fluxo principal

1. Administrador importa pedidos e NFs.
2. Sistema guarda arquivos, detecta duplicidade e processa em segundo plano.
3. Sistema identifica empresa, loja, fornecedor, modelo e itens.
4. Motor compara cada NF com pedidos candidatos e seus saldos.
5. Fila mostra candidata, compatibilidade, alertas e comparação item a item.
6. Administrador aprova, reprova ou escolhe outra planilha.
7. Aprovação cria alocações, atualiza estados e gera cópia preenchida.
8. Administrador confirma posteriormente o recebimento integral da NF.
9. Relatórios consultam todo o histórico e permitem exportação autorizada.

## Módulos

- contas, perfis e escopo por loja;
- empresas, lojas, fornecedores e aliases;
- arquivos e importações;
- pedidos e itens;
- NF-e e itens fiscais;
- conferência, candidatas e sugestões;
- aprovação, associação e alocação;
- exportação de planilha preenchida;
- recebimento e ocorrências;
- relatórios e Dashboard;
- Diagnóstico e reprocessamento;
- auditoria, backup e atualização.

## Não funcionais

- falha de um arquivo não derruba a aplicação;
- mensagens compreensíveis ao usuário e detalhe técnico restrito;
- operações demoradas não bloqueiam navegação;
- reinício não perde tarefas pendentes;
- arquivos e banco possuem backup restaurável;
- caminhos físicos não são identidades de documentos;
- segredos nunca aparecem em texto legível;
- sistema mede duração, falhas, fila, volume e crescimento.

## Critério geral de sucesso

O MVP precisa importar, conferir, explicar, aprovar, recalcular, receber, consultar e auditar sem modificar originais fiscais, duplicar NFs, perder saldos ou exigir manipulação manual de pastas.

