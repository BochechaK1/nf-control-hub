from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import Usuario
from audit.models import EventoAuditoria
from diagnostics.models import Diagnostico
from files.models import Arquivo
from organizations.models import EmpresaCliente, Fornecedor, Loja

from .models import ItemNotaFiscal, NotaFiscal
from .services import import_nfe_xml


KEY = "12345678901234567890123456789012345678901234"


def nfe_xml(
    *,
    key=KEY,
    model="55",
    number="1987853",
    dest_cnpj="11111111000111",
    product_code="000123",
    product_name="Tinta branco",
):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe{key}" versao="4.00">
      <ide>
        <cUF>35</cUF>
        <natOp>Venda</natOp>
        <mod>{model}</mod>
        <serie>1</serie>
        <nNF>{number}</nNF>
        <dhEmi>2026-08-06T10:30:00-03:00</dhEmi>
      </ide>
      <emit>
        <CNPJ>22222222000122</CNPJ>
        <xNome>Coral</xNome>
      </emit>
      <dest>
        <CNPJ>{dest_cnpj}</CNPJ>
        <xNome>Matriz</xNome>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>{product_code}</cProd>
          <cEAN>SEM GTIN</cEAN>
          <xProd>{product_name}</xProd>
          <NCM>32091010</NCM>
          <CFOP>5102</CFOP>
          <uCom>BD</uCom>
          <qCom>10.0000</qCom>
          <vUnCom>99.900000</vUnCom>
          <vProd>999.00</vProd>
          <xPed>W000062885</xPed>
          <nItemPed>1</nItemPed>
        </prod>
      </det>
      <total>
        <ICMSTot>
          <vNF>999.00</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
  <protNFe versao="4.00">
    <infProt>
      <chNFe>{key}</chNFe>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>
""".encode("utf-8")


def xml_upload(content, filename="nfe.xml"):
    return SimpleUploadedFile(filename, content, content_type="application/xml")


class NFeImportTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override = override_settings(NFCH_STORAGE_ROOT=Path(self.tmp.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.empresa = EmpresaCliente.objects.create(nome="Destiny In", codigo="destiny")
        self.loja = Loja.objects.create(
            empresa_cliente=self.empresa,
            codigo="matriz",
            nome="Matriz",
            cnpj="11.111.111/0001-11",
        )
        self.user = Usuario.objects.create_superuser(username="kauan", password="secret")

    def test_authorized_model_55_xml_creates_invoice_and_items(self):
        result = import_nfe_xml(
            empresa_cliente=self.empresa,
            uploaded_file=xml_upload(nfe_xml()),
            usuario=self.user,
        )

        self.assertTrue(result.created)
        self.assertEqual(NotaFiscal.objects.count(), 1)
        nota = NotaFiscal.objects.get()
        self.assertEqual(nota.chave_acesso, KEY)
        self.assertEqual(nota.modelo, "55")
        self.assertEqual(nota.numero, "1987853")
        self.assertEqual(nota.fornecedor.nome, "Coral")
        self.assertEqual(nota.loja, self.loja)
        self.assertEqual(nota.situacao_fila, NotaFiscal.SituacaoFila.AGUARDANDO_MATCH)
        self.assertTrue(
            Fornecedor.objects.filter(
                empresa_cliente=self.empresa,
                cnpj_normalizado="22222222000122",
                nome="Coral",
            ).exists()
        )
        self.assertTrue(
            EventoAuditoria.objects.filter(
                empresa_cliente=self.empresa,
                acao="FORNECEDOR_REGISTRADO_AUTOMATICAMENTE",
                entidade_tipo="Fornecedor",
            ).exists()
        )

        item = ItemNotaFiscal.objects.get()
        self.assertEqual(item.codigo_original, "000123")
        self.assertEqual(item.codigo_normalizado, "123")
        self.assertEqual(item.xped_original, "W000062885")
        self.assertEqual(str(item.quantidade), "10.0000")

    def test_identical_xml_is_duplicate(self):
        content = nfe_xml()
        import_nfe_xml(empresa_cliente=self.empresa, uploaded_file=xml_upload(content), usuario=self.user)
        result = import_nfe_xml(empresa_cliente=self.empresa, uploaded_file=xml_upload(content), usuario=self.user)

        self.assertTrue(result.duplicate)
        self.assertEqual(Arquivo.objects.filter(tipo=Arquivo.Tipo.XML_NFE).count(), 1)
        self.assertEqual(NotaFiscal.objects.count(), 1)

    def test_same_key_with_different_content_becomes_diagnostic(self):
        import_nfe_xml(empresa_cliente=self.empresa, uploaded_file=xml_upload(nfe_xml()), usuario=self.user)
        result = import_nfe_xml(
            empresa_cliente=self.empresa,
            uploaded_file=xml_upload(nfe_xml(product_name="Produto alterado"), filename="nfe-divergente.xml"),
            usuario=self.user,
        )

        self.assertFalse(result.created)
        self.assertEqual(NotaFiscal.objects.count(), 1)
        self.assertEqual(Arquivo.objects.filter(tipo=Arquivo.Tipo.XML_NFE).count(), 2)
        self.assertEqual(Diagnostico.objects.get().tipo, Diagnostico.Tipo.CHAVE_DIVERGENTE)

    def test_unsupported_model_becomes_diagnostic_without_invoice(self):
        result = import_nfe_xml(
            empresa_cliente=self.empresa,
            uploaded_file=xml_upload(nfe_xml(key="22345678901234567890123456789012345678901234", model="65")),
            usuario=self.user,
        )

        self.assertIsNone(result.nota_fiscal)
        self.assertEqual(NotaFiscal.objects.count(), 0)
        self.assertEqual(Diagnostico.objects.get().tipo, Diagnostico.Tipo.DOCUMENTO_NAO_SUPORTADO)

    def test_unknown_store_stays_in_queue_without_diagnostic(self):
        result = import_nfe_xml(
            empresa_cliente=self.empresa,
            uploaded_file=xml_upload(nfe_xml(key="32345678901234567890123456789012345678901234", dest_cnpj="99999999000199")),
            usuario=self.user,
        )

        self.assertTrue(result.created)
        nota = NotaFiscal.objects.get()
        self.assertIsNone(nota.loja)
        self.assertEqual(nota.situacao_fila, NotaFiscal.SituacaoFila.LOJA_DESCONHECIDA)
        self.assertEqual(Diagnostico.objects.count(), 0)

    def test_invoice_header_is_immutable(self):
        import_nfe_xml(empresa_cliente=self.empresa, uploaded_file=xml_upload(nfe_xml()), usuario=self.user)
        nota = NotaFiscal.objects.get()
        nota.numero = "999"

        with self.assertRaises(ValidationError):
            nota.save()
