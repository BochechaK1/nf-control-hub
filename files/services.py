from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
import hashlib
import re

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from audit.models import EventoAuditoria
from audit.services import registrar_evento

from .models import Arquivo


@dataclass(frozen=True)
class StoredFileResult:
    arquivo: Arquivo
    created: bool
    duplicate: bool


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name).strip("._")
    return cleaned or "arquivo"


def store_uploaded_file(*, empresa_cliente, uploaded_file: UploadedFile, usuario, tipo: str) -> StoredFileResult:
    hasher = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    for chunk in uploaded_file.chunks():
        hasher.update(chunk)
        chunks.append(chunk)
        size += len(chunk)

    digest = hasher.hexdigest()
    existing = Arquivo.objects.filter(
        empresa_cliente=empresa_cliente,
        tipo=tipo,
        hash_sha256=digest,
    ).first()
    if existing:
        registrar_evento(
            empresa_cliente=empresa_cliente,
            usuario=usuario,
            origem=EventoAuditoria.Origem.USUARIO,
            entidade=existing,
            acao="ARQUIVO_DUPLICADO",
            motivo=f"Reimportacao binariamente identica de {uploaded_file.name}.",
            metadados={"nome_original": uploaded_file.name, "hash_sha256": digest},
        )
        return StoredFileResult(arquivo=existing, created=False, duplicate=True)

    now = timezone.localtime()
    relative_dir = Path(tipo.lower()) / f"{now:%Y}" / f"{now:%m}"
    filename = f"{uuid4().hex}_{safe_filename(uploaded_file.name)}"
    relative_path = relative_dir / filename
    absolute_path = settings.NFCH_STORAGE_ROOT / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(b"".join(chunks))

    with transaction.atomic():
        arquivo = Arquivo.objects.create(
            empresa_cliente=empresa_cliente,
            tipo=tipo,
            nome_original=uploaded_file.name,
            mime_type=getattr(uploaded_file, "content_type", "") or "",
            tamanho=size,
            hash_sha256=digest,
            caminho_relativo=relative_path.as_posix(),
            usuario_importacao=usuario,
        )
        registrar_evento(
            empresa_cliente=empresa_cliente,
            usuario=usuario,
            origem=EventoAuditoria.Origem.USUARIO,
            entidade=arquivo,
            acao="ARQUIVO_ARMAZENADO",
            depois={
                "tipo": arquivo.tipo,
                "nome_original": arquivo.nome_original,
                "tamanho": arquivo.tamanho,
                "hash_sha256": arquivo.hash_sha256,
            },
        )
    return StoredFileResult(arquivo=arquivo, created=True, duplicate=False)
