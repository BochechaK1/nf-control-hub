# Checklist para publicar no GitHub

Use este checklist antes do primeiro push.

## Antes de subir

1. Confirme que `.env` existe apenas localmente e nao aparece no Git.
2. Confirme que `local_preview.sqlite3` nao aparece no Git.
3. Confirme que `storage/`, `media/`, `staticfiles/`, `tmp/` e `__pycache__/` nao aparecem no Git.
4. Rode os testes:

```powershell
$env:NFCH_ALLOW_SQLITE_TESTS='true'
py manage.py test --settings=nf_control_hub.settings.test
```

5. Rode a checagem do Django:

```powershell
$env:NFCH_ALLOW_SQLITE_TESTS='true'
py manage.py check --settings=nf_control_hub.settings.test
```

## Primeiro envio

Se a pasta ainda nao for um repositorio Git:

```powershell
git init
git add .
git status
git commit -m "Initial NF Control Hub"
git branch -M main
git remote add origin URL_DO_REPOSITORIO
git push -u origin main
```

Antes do `git commit`, confira o `git status`. Nao deve aparecer banco local, XML real, planilha real, exportacao ou `.env`.

## Dados que nunca devem ir ao GitHub

- XML fiscal real
- planilha real de fornecedor
- copia preenchida gerada
- banco SQLite local
- backup de banco
- manifesto de backup com caminhos sensiveis
- `.env` com segredo ou senha
