# Reestruturacao do robo Processamento Automatico DM

## Objetivo

Separar o robo em camadas, reduzindo o acoplamento do antigo `main.py` e aproximando a organizacao do projeto `RoboArquivosSFTP`.

## Estrutura criada

```text
main.py
start/
  processamento_dm.bat
src/
  domain/
    interfaces/
    models/
  application/
    services/
  infrastructure/
    config/
    databases/
    notifications/
    repositories/
  runners/
  shared/
```

## Alteracoes aplicadas

1. Criadas interfaces para executor de banco, repositorio de DM e notificadores.
2. Criado modelo `Cedente` com `dataclass(slots=True, frozen=True)`.
3. Criadas excecoes customizadas em `src/shared/exceptions.py`.
4. Criado executor SQL Server assincrono por interface, usando `asyncio.to_thread` para encapsular `pyodbc`.
5. Migradas queries e procedures para `SQLDmRepository`.
6. Separadas regras em services:
   - `ProcessamentoService`
   - `TransferenciaService`
   - `MailingService`
   - `TelefoneService`
   - `HeartbeatService`
7. Criados notificadores:
   - `TelegramNotifier`
   - `ChatNotifier`
   - `SafeNotifier`
8. Criado runner assincrono em `src/runners/processamento_dm.py`.
9. Criado `start/processamento_dm.bat`.
10. Atualizado `.bat` para apontar para o caminho atual do projeto.

## Fluxos principais

- `ProcessamentoService`: consulta cedentes pendentes, executa `dm.PROC_DATAMART_TB_DIVIDAS`, atualiza status de producao e gera relatorio de carga.
- `TransferenciaService`: consulta cedentes com `Atualizacao_prod > Atualizacao_Espelho`, executa `DB_REPORT.dm.PROC_DATAMART_TRANSFERENCIA_CARTEIRA` e atualiza status de espelho.
- `MailingService`: gera mailing para cedentes elegiveis conforme mapeamento de procedures por cedente.
- `TelefoneService`: executa `Easycollector.dm.Proc_Dm_Tb_Telefones_Pos_Carga`. Por padrao fica desligado, como estava no codigo antigo.
- `HeartbeatService`: atualiza `traces.dbo.TB_PROCESSOS_DADOS` para sinalizar que o robo esta ativo.

## Repositorios por responsabilidade

`src/infrastructure/repositories/dm_repository.py` permanece como fachada para manter compatibilidade com os services existentes.
As responsabilidades ficam separadas em:

```text
src/infrastructure/repositories/processo_dm_repository.py
src/infrastructure/repositories/transferencia_repository.py
src/infrastructure/repositories/mailing_repository.py
src/infrastructure/repositories/telefone_repository.py
src/infrastructure/repositories/heartbeat_repository.py
src/infrastructure/repositories/shared_dm_queries.py
```

## Variaveis novas/opcionais

```text
TELEGRAM_IDS_AUTORIZADOS=6753444201,1680667103
HABILITAR_LOOP_TELEFONES=false
```

## Onde alterar regras agora

- Banco: `src/infrastructure/repositories/*_repository.py`
- Regras de negocio: `src/application/services`
- Loops: `src/runners/processamento_dm.py`
- Configuracoes: `src/infrastructure/config`
- Notificacoes: `src/infrastructure/notifications`

## Observacao sobre `main.py`

O arquivo antigo foi mantido fisicamente, mas recebeu uma entrada refatorada no topo.
Quando executado diretamente, ele inicializa o novo runner assincrono antes de alcancar o codigo legado.
