# Instruções obrigatórias para o Codex

## Fonte de verdade

Antes de alterar o NF Control Hub:

1. leia este arquivo;
2. leia `docs/01-produto-e-escopo.md`;
3. leia os documentos relacionados à tarefa;
4. inspecione código, migrações, testes e alterações existentes;
5. identifique os critérios de aceite aplicáveis.

Se uma regra estiver ausente, ambígua ou contraditória, não invente. Explique o impacto e solicite decisão a Kauan.

## Regras inegociáveis

- XML da NF-e é imutável, permanente e fonte fiscal principal.
- PDF é apenas apoio; não substitui o XML.
- Banco de dados é a fonte operacional de verdade.
- Uma NF pode possuir somente uma associação vigente com um pedido.
- Um pedido pode receber várias NFs.
- Saldo oficial é derivado de alocações aprovadas vigentes.
- Nunca permita saldo negativo ou consumo concorrente do mesmo saldo.
- Toda aprovação, reprovação, anulação, correção, recebimento e exportação relevante é auditável.
- Nenhuma associação é aprovada automaticamente.
- Somente Administrador ou Mestre aprova, reprova, anula e confirma recebimento.
- Visualizador consulta apenas as lojas vinculadas.
- Similaridade de descrição sem código gera sugestão, não match automático.
- Preço da planilha é estimativo e não participa do match.
- Não altere dados fiscais para corrigir cadastro ou associação.
- Não apague XML, auditoria ou registros históricos pelo fluxo comum.
- O MVP funciona somente na rede interna que já alcança o servidor.

## Escopo técnico do MVP

- Python e Django.
- PostgreSQL.
- Servidor Windows existente.
- Instalação nativa, sem Docker.
- Interface web interna.
- Worker separado com fila persistente no banco.
- Excel como pedido; NF-e modelo 55 em XML; PDF opcional.

Docker, Linux, nuvem, acesso público, multiempresa hospedada, aplicativo móvel e inventário físico não entram no MVP.

## Forma de implementação

- Faça uma unidade fechada por vez.
- Preserve alterações do usuário e código não relacionado.
- Use migrações para mudanças no banco.
- Mantenha regra de negócio em serviços/domínio, não em views ou templates.
- Use transações e bloqueios para aprovação, anulação, cancelamento fiscal e recebimento.
- Toda correção de bug deve incluir teste de regressão.
- Parsers devem preservar valor original e produzir valor normalizado separado.
- Erros de arquivo devem virar Diagnóstico, não derrubar a aplicação.
- Não reestruture módulos fora do escopo por preferência técnica.

## Conclusão obrigatória

Antes de declarar uma tarefa concluída:

1. execute testes relevantes;
2. valide o critério de aceite;
3. informe arquivos modificados;
4. informe comandos e resultados dos testes;
5. informe riscos ou pendências reais;
6. atualize a documentação se a regra mudou.

Não oculte testes falhando e não marque como concluído código que não foi validado.

