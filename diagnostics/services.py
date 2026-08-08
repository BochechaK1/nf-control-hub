from .models import Diagnostico


def registrar_diagnostico(
    *,
    empresa_cliente,
    tipo: str,
    mensagem_usuario: str,
    arquivo=None,
    detalhe_tecnico: str = "",
    criado_por=None,
    severidade=Diagnostico.Severidade.ERRO,
    status=Diagnostico.Status.ABERTO,
) -> Diagnostico:
    return Diagnostico.objects.create(
        empresa_cliente=empresa_cliente,
        arquivo=arquivo,
        tipo=tipo,
        status=status,
        severidade=severidade,
        mensagem_usuario=mensagem_usuario,
        detalhe_tecnico=detalhe_tecnico,
        criado_por=criado_por,
    )
