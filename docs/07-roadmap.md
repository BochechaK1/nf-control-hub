# Roadmap fora do MVP atual

Itens abaixo não podem ser implementados durante o Piloto/MVP sem decisão expressa e atualização do escopo.

## Infraestrutura e comercialização

- Docker;
- Linux;
- hospedagem em nuvem;
- acesso público, domínio e HTTPS externo;
- VPN ou túnel como produto;
- vários clientes no mesmo serviço;
- cobrança, assinatura e limites por plano;
- armazenamento de objetos;
- alta disponibilidade;
- atualização central de várias instalações;
- Redis/Celery ou fila distribuída, se as métricas exigirem.

## Produto

- aplicativo móvel;
- integração direta com ShopControl;
- leitura automática de vendas e estoque contínuo;
- eventos fiscais automáticos, carta de correção e cancelamento integrado;
- unificação universal de produtos entre fornecedores;
- aprendizado automático sem confirmação;
- aprovação automática;
- dashboards analíticos avançados;
- personalização/white-label comercial completa.

## Inventário anual

Módulo anotado para desenvolvimento futuro, fora do menu do MVP.

Direção aprovada:

- campanha anual, não estoque contínuo;
- fotografia exportada do ShopControl;
- código interno como identidade principal;
- EAN opcional;
- etiquetas internas para produtos sem código;
- contagem cega por loja e área;
- papel inicialmente permitido;
- digitação posterior no sistema;
- recontagem de divergências;
- auditoria e relatório final.

Arquivo de análise existente: `NF_Control_Hub_Analise_Inventario_2026.md`.

## Critério para promover item ao MVP

1. problema bloqueia o fluxo principal;
2. regra de negócio está escrita;
3. critério de aceite é testável;
4. dados e módulos afetados são conhecidos;
5. não existe entrega segura posterior;
6. Kauan aprova expressamente a mudança.

