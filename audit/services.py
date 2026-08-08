from .models import EventoAuditoria


def registrar_evento(
    *,
    empresa_cliente,
    entidade,
    acao: str,
    usuario=None,
    origem=EventoAuditoria.Origem.USUARIO,
    motivo: str = "",
    antes=None,
    depois=None,
    metadados=None,
):
    return EventoAuditoria.objects.create(
        empresa_cliente=empresa_cliente,
        usuario=usuario,
        origem=origem,
        entidade_tipo=entidade.__class__.__name__,
        entidade_id=str(entidade.pk),
        acao=acao,
        motivo=motivo,
        antes=antes,
        depois=depois,
        metadados=metadados or {},
    )
