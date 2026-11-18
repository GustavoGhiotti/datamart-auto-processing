# Observabilidade do robo de Processamento Automatico DM

## Onde os logs sao gravados

Os logs JSONL sao gravados por processo em:

```text
logs/dm_log.jsonl
logs/transferencia_log.jsonl
logs/mailing_log.jsonl
logs/telefone_log.jsonl
logs/notificacao_log.jsonl
```

Cada linha e um JSON independente com os campos essenciais. Isso permite consultar o arquivo mesmo enquanto o robo esta em execucao.

## Processos registrados

O robo registra eventos para:

- `DM`
- `Transferencia`
- `Telefones`
- `Mailing`
- `Notificacao`

## Campos principais

Cada evento pode conter:

- `camada`
- `tipo_evento`
- `inicio`
- `fim`
- `processo`
- `etapa_processo`
- `status`: `iniciado`, `sucesso`, `aviso` ou `erro`
- `carteira`
- `duracao_segundos`
- `quantidade_registros`
- `mensagem`

## Exemplos de consulta

PowerShell, ultimos eventos:

```powershell
Get-Content logs\mailing_log.jsonl -Tail 20
```

PowerShell, somente erros:

```powershell
Get-Content logs\mailing_log.jsonl | Select-String '"status":"erro"'
```

PowerShell, somente mailing:

```powershell
Get-Content logs\mailing_log.jsonl
```

PowerShell, uma carteira/cedente especifico:

```powershell
Get-Content logs\mailing_log.jsonl | Select-String '"carteira":"3"'
```

## Google_Message e chat interno

O erro informado ocorre no envio de notificacao para o chat interno.

No codigo Python, o ponto de chamada e:

```text
src/infrastructure/notifications/chat_notifier.py
```

O Python executa:

```sql
EXEC [Traces].[dbo].[Proc_mensagem_chat] ?
```

Pelo erro retornado pelo SQL Server, essa procedure chama a rotina CLR:

```text
Google_Message
```

O timeout acontece dentro da chamada HTTP feita por essa rotina CLR, nao dentro do fluxo principal do robo.

Melhoria aplicada:

- `ChatNotifier` agora faz retry controlado.
- Cada falha de tentativa e registrada como `aviso`.
- Apos esgotar as tentativas, `SafeNotifier` registra novo `aviso`.
- O fluxo principal nao quebra apenas porque a notificacao do chat falhou.

Ponto a validar no banco:

- Confirmar se `Traces.dbo.Proc_mensagem_chat` permite configurar timeout da rotina `Google_Message`.
- Confirmar se a rotina CLR tem timeout fixo no assembly.
- Avaliar com o DBA se o endpoint do Google Chat estava lento ou indisponivel no horario do erro.

## Dados sensiveis

O logger mascara alguns padroes sensiveis antes de gravar:

- CPF/CNPJ numerico em formato continuo.
- E-mail.

O robo nao grava payloads completos de clientes. Os logs focam em carteira, processo, etapa, procedure e erro tecnico.
