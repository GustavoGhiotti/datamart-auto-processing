from __future__ import annotations

import asyncio

from src.domain.interfaces.database_executor import DatabaseExecutor
from src.infrastructure.repositories.shared_dm_queries import as_rows
from src.shared.robot_logger import robot_logger


CEDENTES_APENAS_FLUXO_DM = frozenset({3})


class MailingRepository:
    def __init__(
        self,
        *,
        db_71_dashpulse: DatabaseExecutor,
        db_71_planejamento: DatabaseExecutor,
    ) -> None:
        self._db_71_dashpulse = db_71_dashpulse
        self._db_71_planejamento = db_71_planejamento

    async def listar_cedentes_mailing(self) -> list[int]:
        resultado = await self._db_71_dashpulse.execute(
            query="""
                SELECT
                    ID_CEDENTE,
                    nm_cedente
                FROM DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA WITH(NOLOCK)
                WHERE Atualizacao_espelho >= Atualizacao_prod
                  AND CAST(Atualizacao_espelho AS DATE) = CAST(GETDATE() AS DATE)
                  AND (
                        Atualizacao_mailing IS NULL
                        OR Atualizacao_mailing < Atualizacao_espelho
                      )
                  AND CAST(Atualizacao_Telefone AS DATE) = CAST(GETDATE() AS DATE);
            """,
            fetch=True,
        )

        return [int(row["ID_CEDENTE"]) for row in as_rows(resultado)]

    async def gerar_mailing(self, id_cedente: int) -> bool:
        procedures = self._get_procedures_mailing(id_cedente)

        if not procedures:
            robot_logger.warning(
                processo="Mailing",
                etapa="buscar_procedures_mailing",
                carteira=id_cedente,
                mensagem="Cedente sem procedure de mailing mapeada.",
                detalhes={"id_cedente": id_cedente},
            )
            return False

        for procedure in procedures:
            await self._executar_procedure(
                procedure=procedure,
                carteira=id_cedente,
                etapa="executar_procedure_mailing",
                interromper_em_erro=True,
            )

        return True

    async def gerar_mailing_diario(self) -> int:
        return await self._rodar_mailing_diario()

    async def listar_cedentes_mailing_diario(self) -> list[int]:
        return sorted(self._get_mapeamento_mailing_diario())

    async def listar_procedures_mailing_diario(self) -> list[str]:
        return self._get_procedures_mailing_diario()

    async def marcar_atualizacao_mailing(self, id_cedente: int) -> None:
        await self._db_71_dashpulse.execute(
            query="""
                UPDATE DB_DASHPULSE.dbo.TB_ATUALIZACAO_DM_CARTEIRA
                SET Atualizacao_mailing = GETDATE()
                WHERE ID_CEDENTE = ?
            """,
            parametros=(id_cedente,),
            fetch=False,
        )

    def _get_procedures_mailing(self, id_cedente: int) -> list[str]:
        return self._get_mapeamento_mailing().get(id_cedente, [])

    def _get_mapeamento_mailing_diario(self) -> dict[int, list[str]]:
        return {
            id_cedente: procedures
            for id_cedente, procedures in self._get_mapeamento_mailing().items()
            if id_cedente not in CEDENTES_APENAS_FLUXO_DM
        }

    def _get_procedures_apenas_fluxo_dm(self) -> set[str]:
        mapeamento = self._get_mapeamento_mailing()
        procedures: set[str] = set()

        for id_cedente in CEDENTES_APENAS_FLUXO_DM:
            procedures.update(mapeamento.get(id_cedente, []))

        return procedures

    async def _executar_procedure(
        self,
        *,
        procedure: str,
        carteira: str | int,
        etapa: str,
        interromper_em_erro: bool,
    ) -> bool:
        query = f"EXEC {procedure}"
        timer = robot_logger.start(
            processo="Mailing",
            etapa=etapa,
            carteira=carteira,
            query=query,
            detalhes={"procedure": procedure},
        )

        try:
            await self._db_71_planejamento.execute(
                query=query,
                fetch=False,
                timeout=1200,
                autocommit=True,
            )
            robot_logger.success(timer, query=query)
            return True
        except Exception as error:
            robot_logger.error(
                timer,
                error=error,
                query=query,
                detalhes={"procedure": procedure},
            )
            if interromper_em_erro:
                raise
            return False

    async def _executar_procedures_em_threads(
        self,
        procedures: list[str],
        *,
        max_workers: int = 3,
        etapa: str = "executar_procedure_mailing_diario",
    ) -> int:
        if not procedures:
            robot_logger.warning(
                processo="Mailing",
                etapa=etapa,
                carteira="diario",
                mensagem="Nenhuma procedure encontrada para o mailing diario.",
            )
            return 0

        total_sucesso = 0

        for inicio_lote in range(0, len(procedures), max_workers):
            lote = procedures[inicio_lote : inicio_lote + max_workers]
            robot_logger.warning(
                processo="Mailing",
                etapa="iniciar_lote_mailing_diario",
                carteira="diario",
                mensagem=f"Iniciando lote com {len(lote)} procedure(s).",
                detalhes={
                    "inicio_lote": inicio_lote,
                    "max_workers": max_workers,
                    "procedures": lote,
                },
            )
            resultados = await asyncio.gather(
                *(
                    self._executar_procedure(
                        procedure=procedure,
                        carteira="diario",
                        etapa=etapa,
                        interromper_em_erro=False,
                    )
                    for procedure in lote
                )
            )
            total_sucesso += sum(1 for resultado in resultados if resultado)

        return total_sucesso

    async def _rodar_mailing_diario(self) -> int:
        procedures = self._get_procedures_mailing_diario()
        return await self._executar_procedures_em_threads(procedures, max_workers=3)

    def _get_procedures_mailing_diario(self) -> list[str]:
        procedures: list[str] = []
        procedures_adicionadas: set[str] = set()
        procedures_apenas_fluxo_dm = self._get_procedures_apenas_fluxo_dm()

        for procedures_cedente in self._get_mapeamento_mailing_diario().values():
            for procedure in procedures_cedente:
                if procedure in procedures_apenas_fluxo_dm:
                    continue

                if procedure in procedures_adicionadas:
                    continue

                procedures.append(procedure)
                procedures_adicionadas.add(procedure)

        return procedures

    def _get_mapeamento_mailing(self) -> dict[int, list[str]]:
        mailing_por_cedente = {
            1002: ["[DB_PLANEJAMENTO].[raw].[EXPORT_MAILING_UPSILON_NOVO_V2]"],
            110: ["[DB_PLANEJAMENTO].[Raw].[EXPORT_MAILING_CLARA]"],
            105: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Banco_Lambda]"],
            99: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_teta_IMOBILIARIO]"],
            94: [
                "[DB_PLANEJAMENTO].[Raw].[BASE_DINAMICA_BANCO_IOTA]",
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Banco_Iota]",
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Banco_Iota_DESCUMPRIDO]",
            ],
            90: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_ARC4]"],
            88: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Gama_Reconquista]"],
            86: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_teta_INVESTFLEX]"],
            84: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_TETA_SWAT]"],
            81: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_beta_V1]"],
            77: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_teta]"],
            71: ["[DB_PLANEJAMENTO].[Raw].[EXPORT_MAILING_ZETA_NOVO_V3]"],
            67: [
                "[DB_PLANEJAMENTO].[Raw].[Base_Dinamica_Sigma_consumer]",
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_sigma_consumer_novo]",
            ],
            61: [
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_ativos]",
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Ativos_Preventivo]",
            ],
            60: ["[DB_PLANEJAMENTO].[Raw].[EXPORT_MAILING_PI_V3]"],
            54: [
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_ativos]",
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Ativos_Preventivo]",
            ],
            53: [
                "[DB_PLANEJAMENTO].[Raw].[Base_Dinamica_Sigma_autos]",
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_sigma_autos_novo]",
            ],
            51: ["[DB_PLANEJAMENTO].[Raw].[BASE_DINAMICA_BANCOALFA_NOVO]"],
            43: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_RHO_V4]"],
            14: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Nu_WO]"],
            4: [
                "[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Gama]",
                "[DB_PLANEJAMENTO].[Raw].[BASE_DINAMICA_GAMA_CONSIG_NOVO]",
                "[DB_PLANEJAMENTO].[Raw].[EXPORT_MAILING_GAMA_CONSIG_NOVO]",
            ],
            3: ["[DB_PLANEJAMENTO].[Raw].[Export_Mailing_Mu]"],
        }

        return mailing_por_cedente
