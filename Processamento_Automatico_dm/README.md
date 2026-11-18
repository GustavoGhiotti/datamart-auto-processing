# Processamento Automatico DM

Robo responsavel por processar o datamart de dividas, transferir carteiras para o ambiente 71, gerar mailing elegivel, registrar heartbeat e enviar notificacoes.

## Mapa geral dos fluxos

O robo comeca em `main.py`. Esse arquivo monta os servicos em `src/infrastructure/config/factories.py` e entrega tudo para `src/runners/processamento_dm.py`, que inicia os loops paralelos.

Fluxo tecnico geral:

```text
main.py
  -> criar_servicos()
  -> executar_loops()
  -> loop especifico
  -> service de aplicacao
  -> SQLDmRepository
  -> SQLServerExecutor
  -> SQL Server / Telegram / Chat interno
```

## Fluxo de processamento do datamart

Onde comeca:

- `main.py` inicia o robo.
- `executar_loops()` cria `loop_atualizacao()`.
- `loop_atualizacao()` chama `ProcessamentoService.executar_um()`.

Arquivos e funcoes:

- `src/runners/processamento_dm.py`: `loop_atualizacao`
- `src/application/services/processamento_service.py`: `atualizar_relatorio_carga`, `executar_um`
- `src/infrastructure/repositories/processo_dm_repository.py`: `listar_cedentes_para_processar`, `processar_carteira`, `marcar_atualizacao_prod`, `atualizar_relatorio_carga`
- `src/infrastructure/repositories/dm_repository.py`: fachada de compatibilidade usada pelos services

De onde vem os dados:

- `DB_DASHPULSE.dbo.VIEW_CONTROLE_SCC`, filtrando `ATUALIZACAO_EXEC = 0`.
- `easycollector.dm.TB_DIVIDAS`, filtrando `STATUS_ATUAL = 1`.

Processamentos:

- Atualiza o relatorio de carga com `easycollector.dbo.PRC_MIS_GERA_RELATORIO_CARGAS`.
- Cruza os cedentes pendentes da view de controle com os cedentes ativos no datamart.
- Processa somente o primeiro cedente elegivel do ciclo.
- Executa `dm.PROC_DATAMART_TB_DIVIDAS ?`.
- Marca `Atualizacao_prod = GETDATE()` em `DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA`.
- Atualiza novamente o relatorio de carga apos sucesso.

Retornos e destinos:

- Retorna `True` quando tratou um cedente e `False` quando nao encontrou fila.
- O retorno volta para o loop decidir se espera `2` ou `300` segundos.
- Mensagens de inicio, sucesso e erro vao para Telegram.
- O status de producao fica na tabela `TB_ATUALIZACAO_DM_CARTEIRA`.

## Fluxo de transferencia para o ambiente 71

Onde comeca:

- `executar_loops()` cria `loop_transferencia()`.
- `loop_transferencia()` chama `TransferenciaService.executar_um()`.

Arquivos e funcoes:

- `src/runners/processamento_dm.py`: `loop_transferencia`
- `src/application/services/transferencia_service.py`: `executar_um`
- `src/infrastructure/repositories/transferencia_repository.py`: `listar_cedentes_para_transferir`, `transferir_carteira`, `marcar_atualizacao_espelho`
- `src/infrastructure/repositories/dm_repository.py`: fachada de compatibilidade usada pelos services
- `src/infrastructure/notifications/telegram_notifier.py`: `send`
- `src/infrastructure/notifications/chat_notifier.py`: `send`

De onde vem os dados:

- `DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA`, quando `Atualizacao_prod > Atualizacao_Espelho`.
- `easycollector.dm.TB_DIVIDAS`, para recuperar a carteira do cedente.

Processamentos:

- Cruza a fila de transferencia com os cedentes ativos no datamart.
- Processa somente o primeiro cedente elegivel do ciclo.
- Envia aviso de inicio para Telegram e chat interno.
- Executa `DB_REPORT.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA ?`.
- Marca `Atualizacao_espelho = GETDATE()`.

Retornos e destinos:

- Retorna `True` quando tratou um cedente e `False` quando nao encontrou fila.
- Mensagens detalhadas vao para Telegram.
- Mensagens resumidas vao para o chat interno via `Traces.dbo.Proc_mensagem_chat`.
- O status de espelho fica na tabela `TB_ATUALIZACAO_DM_CARTEIRA`.

## Fluxo de mailing

Onde comeca:

- `executar_loops()` cria `loop_mailing()`.
- `loop_mailing()` chama `MailingService.executar_pendentes()`.

Arquivos e funcoes:

- `src/runners/processamento_dm.py`: `loop_mailing`
- `src/application/services/mailing_service.py`: `executar_pendentes`
- `src/infrastructure/repositories/mailing_repository.py`: `listar_cedentes_mailing`, `gerar_mailing`, `marcar_atualizacao_mailing`
- `src/infrastructure/repositories/dm_repository.py`: fachada de compatibilidade usada pelos services

De onde vem os dados:

- `DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA`.
- A fila exige espelho atualizado no dia, espelho maior ou igual a producao, e mailing nulo ou anterior ao espelho.

Processamentos:

- Percorre todos os cedentes pendentes retornados no ciclo.
- Chama `gerar_mailing(id_cedente)`.
- Busca as procedures no mapeamento de mailing por cedente.
- Executa todas as procedures mapeadas para o cedente.
- Apos sucesso, marca `Atualizacao_mailing = GETDATE()`.

Retornos e destinos:

- Retorna a quantidade de mailings gerados.
- Mensagens de sucesso ou erro vao para Telegram.
- O status de mailing fica na tabela `TB_ATUALIZACAO_DM_CARTEIRA`.

Ponto a validar:

- Cedentes pendentes sem mapeamento de procedure sao registrados como aviso e nao geram mailing.

## Fluxo de atualizacao de telefones

Onde comeca:

- `executar_loops()` cria `loop_telefones()` somente quando `HABILITAR_LOOP_TELEFONES=true`.
- `loop_telefones()` chama `TelefoneService.executar_um()`.

Arquivos e funcoes:

- `src/runners/processamento_dm.py`: `loop_telefones`
- `src/application/services/telefone_service.py`: `executar_um`
- `src/infrastructure/repositories/transferencia_repository.py`: `listar_cedentes_para_transferir`
- `src/infrastructure/repositories/telefone_repository.py`: `atualizar_telefones`
- `src/infrastructure/repositories/dm_repository.py`: fachada de compatibilidade usada pelos services

De onde vem os dados:

- Reaproveita a mesma fila da transferencia: `Atualizacao_prod > Atualizacao_Espelho`.
- Usa `easycollector.dm.TB_DIVIDAS` para identificar a carteira.

Processamentos:

- Verifica se existe cedente elegivel.
- Executa `Easycollector.dm.Proc_Dm_Tb_Telefones_Pos_Carga`.
- Envia mensagens de inicio, sucesso ou erro.

Retornos e destinos:

- Retorna `True` quando havia cedente de referencia para disparar o fluxo.
- Retorna `False` quando nao havia cedente elegivel.
- Mensagens vao para Telegram.

Ponto a validar:

- Confirmar se telefones devem depender da fila de transferencia ou se precisam de fila propria.

## Fluxo de heartbeat

Onde comeca:

- `executar_loops()` cria `loop_heartbeat()`.
- `loop_atualizacao()` tambem chama heartbeat quando esta em horario bloqueado.

Arquivos e funcoes:

- `src/runners/processamento_dm.py`: `loop_heartbeat`
- `src/application/services/heartbeat_service.py`: `executar`
- `src/infrastructure/repositories/heartbeat_repository.py`: `registrar_heartbeat`
- `src/infrastructure/repositories/dm_repository.py`: fachada de compatibilidade usada pelos services

De onde vem os dados:

- Nao depende de fila externa.

Processamentos:

- Atualiza `traces.dbo.TB_PROCESSOS_DADOS`.
- Preenche `DT_ATUALIZACAO`, `DT_HR_ATUALIZACAO` e `Status`.
- O registro alvo e `ID_PROCESSO = 2`.

Retornos e destinos:

- Nao retorna valor de negocio.
- O retorno pratico e o update no banco `Traces`.
- Em caso de falha, o runner imprime aviso no console e continua.

Ponto a validar:

- Confirmar se `ID_PROCESSO = 2` e fixo para este robo em todos os ambientes.

## Fluxo de notificacoes

Onde comeca:

- Os services chamam `Notifier.send()`.
- A implementacao concreta e montada em `criar_servicos()`.

Arquivos e funcoes:

- `src/infrastructure/notifications/telegram_notifier.py`: envia para Telegram.
- `src/infrastructure/notifications/chat_notifier.py`: envia para chat interno.
- `src/infrastructure/notifications/safe_notifier.py`: captura falhas de envio.

De onde vem os dados:

- Mensagens montadas pelos services.
- `TELEGRAM_TOKEN`, `GRUPO_DADOS` e `TELEGRAM_IDS_AUTORIZADOS` do `.env`.
- Banco `Traces` para envio ao chat interno.

Processamentos:

- Telegram envia para o grupo e para usuarios autorizados.
- Chat interno executa `Traces.dbo.Proc_mensagem_chat`.
- `SafeNotifier` imprime aviso quando a notificacao falha.

Retornos e destinos:

- Nao ha retorno de negocio.
- Saidas vao para Telegram, chat interno ou console em caso de falha.

## Janelas e cadencia

- Os fluxos principais pausam entre 21h e 4h.
- Quando nao ha trabalho, os loops aguardam `300` segundos.
- Quando houve processamento, os loops principais aguardam `2` segundos.
- O loop de telefones, quando habilitado e sem trabalho, aguarda `1200` segundos.

## Logs e observabilidade

O robo grava logs JSONL separados por processo em:

```text
logs/dm_log.jsonl
logs/transferencia_log.jsonl
logs/mailing_log.jsonl
logs/telefone_log.jsonl
logs/notificacao_log.jsonl
```

Cada linha e um JSON independente. Os campos `camada` e `tipo_evento` identificam que o registro veio do logger; o campo `etapa_processo` mostra qual etapa real do fluxo estava em execucao.

Campos principais:

- `camada`
- `tipo_evento`
- `processo`
- `etapa_processo`
- `status`
- `carteira`
- `inicio`
- `fim`
- `duracao_segundos`
- `quantidade_registros`
- `mensagem`

Processos cobertos:

- `DM`
- `Transferencia`
- `Telefones`
- `Mailing`
- `Notificacao`

Consultas rapidas:

```powershell
Get-Content logs\mailing_log.jsonl -Tail 20
Get-Content logs\dm_log.jsonl | Select-String '"status":"erro"'
Get-Content logs\transferencia_log.jsonl | Select-String '"carteira"'
```

Detalhes adicionais estao em:

```text
documentacao/observabilidade_mailing_dm_telefones.md
```

## Resumo dos services

- `ProcessamentoService`: consulta cedentes pendentes, executa `dm.PROC_DATAMART_TB_DIVIDAS`, atualiza status de producao e gera relatorio de carga.
- `TransferenciaService`: consulta cedentes com `Atualizacao_prod > Atualizacao_Espelho`, executa `DB_REPORT.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA` e atualiza status de espelho.
- `MailingService`: gera mailing para cedentes elegiveis conforme mapeamento de procedures por cedente.
- `TelefoneService`: executa `Easycollector.dm.Proc_Dm_Tb_Telefones_Pos_Carga`. Por padrao fica desligado, como estava no codigo antigo.
- `HeartbeatService`: atualiza `traces.dbo.TB_PROCESSOS_DADOS` para sinalizar que o robo esta ativo.

## Execucao

```bash
python main.py
```

Ou pelo arquivo:

```text
start/processamento_dm.bat
```

## Variaveis de ambiente

Obrigatorias:

```text
TELEGRAM_TOKEN
GRUPO_DADOS
DB_65
DB_71
DB_USUARIO_65
DB_SENHA_65
DB_USUARIO_71
DB_SENHA_71
```

Opcionais:

```text
TELEGRAM_IDS_AUTORIZADOS=6753444201,1680667103
HABILITAR_LOOP_TELEFONES=false
```

## Observacoes tecnicas

- O acesso a SQL Server fica em `src/infrastructure/databases/sql_server_executor.py`.
- As queries e procedures ficam separadas em `src/infrastructure/repositories/*_repository.py`.
- `src/infrastructure/repositories/dm_repository.py` permanece como fachada para preservar compatibilidade.
- As regras de negocio ficam em `src/application/services`.
- Os loops continuos ficam em `src/runners/processamento_dm.py`.
- As queries com `id_cedente` foram parametrizadas com `?` do `pyodbc`.
- Notificacoes sao protegidas por `SafeNotifier`, evitando que falha no Telegram ou chat derrube o loop principal.
