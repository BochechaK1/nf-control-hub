# Arquitetura técnica do MVP

## Stack

- Python + Django;
- PostgreSQL;
- templates Django e Bootstrap, com interações pontuais;
- OpenPyXL para Excel;
- parser XML seguro para NF-e;
- PDF somente como apoio;
- servidor WSGI compatível com Windows, nunca `runserver` em produção.

## Implantação

- servidor Windows existente;
- ambiente virtual Python isolado;
- aplicação e worker como serviços do Windows;
- 5 a 8 usuários simultâneos;
- acesso somente na rede interna já conectada;
- firewall limitado às redes necessárias;
- PostgreSQL acessível somente pela aplicação/host autorizado;
- sem Docker, Linux, nuvem ou internet pública no MVP.

## Camadas sugeridas

- `accounts`: autenticação, perfis e escopos;
- `organizations`: empresas, lojas e fornecedores;
- `files`: armazenamento, hash e retenção;
- `orders`: pedidos, itens e modelos Excel;
- `invoices`: NF-e e itens fiscais;
- `matching`: normalização, candidatas, métricas e sugestões;
- `approvals`: decisões, associações e alocações;
- `receiving`: recebimentos e ocorrências;
- `reports`: consultas e exportações;
- `diagnostics`: tarefas, falhas e reprocessamento;
- `audit`: eventos imutáveis.

Views e templates não devem conter cálculo de saldo ou regra de match.

## Processamento em segundo plano

No MVP, usar fila persistente no PostgreSQL e worker separado.

Estados:

- `AGUARDANDO`
- `PROCESSANDO`
- `CONCLUIDO`
- `ERRO`
- `CANCELADO`

Requisitos:

- claim atômico da tarefa;
- idempotência por tipo e arquivo;
- heartbeat/timeout para recuperar tarefa abandonada;
- tentativas limitadas;
- progresso e erro compreensível;
- reinício sem perda;
- concorrência configurável;
- reprocessamento pelo Diagnóstico.

## Armazenamento

- arquivos ativos em diretório controlado fora da pasta de upload do usuário;
- nomes físicos gerados pelo sistema;
- hash calculado antes do processamento;
- temporários em diretório separado;
- publicação atômica do arquivo final;
- XML permanente;
- banco nunca dentro de pasta sincronizada.

## Backup

1. gerar `pg_dump` consistente;
2. copiar arquivos controlados de forma consistente;
3. produzir manifesto com hashes e data;
4. guardar várias gerações;
5. sincronizar somente o backup pronto com OneDrive/destino externo;
6. testar restauração periodicamente.

Sincronização simples não substitui backup.

## Atualização

Atualização central iniciada por Kauan no servidor:

1. validar pacote/versão;
2. backup prévio;
3. parar serviços;
4. atualizar código e dependências controladas;
5. executar migrações;
6. coletar arquivos estáticos;
7. iniciar serviços;
8. executar health check;
9. permitir rollback documentado.

Não implementar atualização autônoma silenciosa no MVP.

## Segurança

- autenticação individual;
- senhas com hash do Django;
- recuperação aprovada por administrador e senha temporária de uso controlado;
- troca obrigatória no primeiro login temporário;
- encerramento de sessões por administrador;
- proteção CSRF, validação de uploads e limites de tamanho;
- parser XML sem entidades externas;
- nomes de arquivos não usados como caminhos confiáveis;
- segredos fora do código;
- detalhe técnico restrito a administradores;
- log sem senhas, tokens ou XML completo desnecessário.

## Desempenho

- importação não bloqueia requisição web;
- paginação nas listas;
- índices por empresa, CNPJ, chave, fornecedor, loja, status e datas;
- consultas sempre escopadas por empresa/loja;
- métricas de duração, fila, falha, volume e crescimento;
- cache de saldo reconstruível.

