import logging
import re
from datetime import date
from typing import Optional

from sqlalchemy import create_engine, text


# =============================================================================
# Configuração de logs
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# =============================================================================
# Funções auxiliares
# =============================================================================

def validar_identificador(valor: str) -> str:
    """
    Valida identificadores SQL usados dinamicamente, como schemas,
    tabelas e nomes de índices.
    """
    if not isinstance(valor, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*",
        valor,
    ):
        raise ValueError(
            f"Identificador SQL inválido: {valor!r}. "
            "Use somente letras, números e underscore."
        )

    return valor


def tabela_ref(schema: str, tabela: str) -> str:
    """
    Retorna uma referência segura para schema.tabela.
    """
    schema = validar_identificador(schema)
    tabela = validar_identificador(tabela)

    return f'"{schema}"."{tabela}"'


def primeiro_dia_mes(data_referencia: date) -> date:
    """
    Normaliza uma data para o primeiro dia do mês.
    """
    return date(
        data_referencia.year,
        data_referencia.month,
        1,
    )


# =============================================================================
# Estrutura persistida de agregações mensais
# =============================================================================

def criar_tabela_clima_mensal(
    engine,
    schema: str,
    tabela_horaria: str,
    tabela_mensal: str,
) -> None:
    """
    Cria ou ajusta a tabela mensal por estação.

    Os nomes de colunas são mantidos em minúsculo para compatibilidade
    com o restante do pipeline climático.
    """
    schema = validar_identificador(schema)
    tabela_horaria = validar_identificador(tabela_horaria)
    tabela_mensal = validar_identificador(tabela_mensal)

    tabela_horaria_ref = tabela_ref(schema, tabela_horaria)
    tabela_mensal_ref = tabela_ref(schema, tabela_mensal)

    logger.info(
        "Criando ou validando tabela mensal: %s",
        tabela_mensal_ref,
    )

    queries = [
        f'CREATE SCHEMA IF NOT EXISTS "{schema}";',
        f"""
        CREATE TABLE IF NOT EXISTS {tabela_mensal_ref} (
            codigo_estacao VARCHAR(20) NOT NULL,
            dt_ref DATE NOT NULL,
            ano_mes INTEGER NOT NULL,
            n_registros INTEGER NOT NULL,

            precipitacao_total DOUBLE PRECISION,
            precipitacao_media DOUBLE PRECISION,
            qtd_dias_chuva INTEGER,

            pressao_atm DOUBLE PRECISION,
            radiacao DOUBLE PRECISION,

            temp_ar DOUBLE PRECISION,
            temp_max DOUBLE PRECISION,
            temp_min DOUBLE PRECISION,

            amplitude_t_max DOUBLE PRECISION,
            amplitude_t_min DOUBLE PRECISION,
            amplitude_t_media DOUBLE PRECISION,

            qtd_dias_calor_intenso INTEGER,
            max_seq_dias_chuva INTEGER,
            max_seq_dias_calor_intenso INTEGER,

            umid_max DOUBLE PRECISION,
            umid_min DOUBLE PRECISION,
            umid_ar DOUBLE PRECISION,

            amplitude_u_max DOUBLE PRECISION,
            amplitude_u_media DOUBLE PRECISION,

            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (codigo_estacao, dt_ref)
        );
        """,

        # Compatibilidade com uma tabela mensal que já existia antes
        # de as novas features serem adicionadas.
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS precipitacao_total DOUBLE PRECISION;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS precipitacao_media DOUBLE PRECISION;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS qtd_dias_chuva INTEGER;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS amplitude_t_max DOUBLE PRECISION;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS amplitude_t_min DOUBLE PRECISION;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS amplitude_t_media DOUBLE PRECISION;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS qtd_dias_calor_intenso INTEGER;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS max_seq_dias_chuva INTEGER;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS max_seq_dias_calor_intenso INTEGER;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS amplitude_u_max DOUBLE PRECISION;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS amplitude_u_media DOUBLE PRECISION;
        """,
        f"""
        ALTER TABLE {tabela_mensal_ref}
        ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP;
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{tabela_mensal}_dt_ref"
        ON {tabela_mensal_ref} (dt_ref);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{tabela_mensal}_ano_mes"
        ON {tabela_mensal_ref} (ano_mes);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{tabela_horaria}_data_estacao"
        ON {tabela_horaria_ref} (
            "DATA_HORA",
            "CODIGO_ESTACAO"
        );
        """,
    ]

    with engine.begin() as conn:
        for query in queries:
            conn.execute(text(query))


# =============================================================================
# Agregações INMET: horário -> diário -> mensal
# =============================================================================

def atualizar_clima_mensal(
    db_uri: str,
    schema: str = "modelos",
    tabela_horaria: str = "bz_inmet_horarios",
    tabela_mensal: str = "bz_inmet_clima_mensal",
    data_inicio: Optional[date] = None,
    reprocessar_completo: bool = False,
    limite_chuva_mm: float = 1.0,
    limite_calor_intenso_c: float = 35.0,
) -> int:
    """
    Cria e atualiza dados mensais de clima por estação.

    Etapas
    ------
    1. Agrega dados horários em métricas diárias.
    2. Calcula indicadores diários de chuva e calor intenso.
    3. Calcula sequências consecutivas de dias com chuva e calor intenso.
    4. Consolida todas as métricas no nível mensal.

    Parâmetros
    ----------
    db_uri:
        DATABASE_URL recebido do pipeline principal.

    schema:
        Schema das tabelas INMET.

    tabela_horaria:
        Tabela de origem com dados horários.

    tabela_mensal:
        Tabela persistida com agregações mensais.

    data_inicio:
        Primeiro mês a recalcular. Ignorado se
        reprocessar_completo=True.

    reprocessar_completo:
        Se True, remove e reconstrói todas as agregações mensais.

    limite_chuva_mm:
        Precipitação total mínima diária, em mm, para classificar
        um dia como chuvoso.

    limite_calor_intenso_c:
        Temperatura máxima diária mínima, em °C, para classificar
        um dia como de calor intenso.

    Retorno
    -------
    int:
        Quantidade de linhas mensais inseridas ou atualizadas.
    """
    if not db_uri:
        raise ValueError("db_uri não foi informado.")

    if limite_chuva_mm < 0:
        raise ValueError("limite_chuva_mm não pode ser negativo.")

    schema = validar_identificador(schema)
    tabela_horaria = validar_identificador(tabela_horaria)
    tabela_mensal = validar_identificador(tabela_mensal)

    engine = create_engine(db_uri)

    tabela_horaria_ref = tabela_ref(schema, tabela_horaria)
    tabela_mensal_ref = tabela_ref(schema, tabela_mensal)

    try:
        criar_tabela_clima_mensal(
            engine=engine,
            schema=schema,
            tabela_horaria=tabela_horaria,
            tabela_mensal=tabela_mensal,
        )

        with engine.connect() as conn:
            possui_dados_horarios = conn.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {tabela_horaria_ref}
                    );
                """)
            ).scalar()

        if not possui_dados_horarios:
            logger.warning(
                "A tabela horária %s não possui dados. "
                "A agregação mensal não será executada.",
                tabela_horaria_ref,
            )
            return 0

        if reprocessar_completo:
            logger.info(
                "Reprocessando toda a tabela mensal %s...",
                tabela_mensal_ref,
            )

            with engine.begin() as conn:
                conn.execute(text(f"TRUNCATE TABLE {tabela_mensal_ref};"))

            data_inicio_processamento = None

        elif data_inicio is not None:
            data_inicio_processamento = primeiro_dia_mes(data_inicio)

            logger.info(
                "Atualizando agregações mensais desde %s...",
                data_inicio_processamento.isoformat(),
            )

        else:
            with engine.connect() as conn:
                ultimo_mes_processado = conn.execute(
                    text(f"""
                        SELECT MAX(dt_ref)
                        FROM {tabela_mensal_ref};
                    """)
                ).scalar()

            data_inicio_processamento = (
                primeiro_dia_mes(ultimo_mes_processado)
                if ultimo_mes_processado is not None
                else None
            )

            if data_inicio_processamento is None:
                logger.info(
                    "Tabela mensal vazia. Processando todo o histórico INMET..."
                )
            else:
                logger.info(
                    "Atualizando agregações mensais a partir de %s...",
                    data_inicio_processamento.isoformat(),
                )

        filtro_data = ""
        parametros = {
            "limite_chuva_mm": limite_chuva_mm,
            "limite_calor_intenso_c": limite_calor_intenso_c,
        }

        if data_inicio_processamento is not None:
            filtro_data = """
                WHERE h."DATA_HORA" >= :data_inicio
            """

            parametros["data_inicio"] = data_inicio_processamento

            with engine.begin() as conn:
                conn.execute(
                    text(f"""
                        DELETE FROM {tabela_mensal_ref}
                        WHERE dt_ref >= :data_inicio;
                    """),
                    {
                        "data_inicio": data_inicio_processamento,
                    },
                )

        query_agregacao = text(f"""
            WITH diario AS (
                SELECT
                    h."CODIGO_ESTACAO" AS codigo_estacao,
                    DATE_TRUNC('day', h."DATA_HORA")::DATE AS dt_dia,

                    COUNT(*)::INTEGER AS n_registros_dia,

                    SUM(h."PRECIPITACAO") AS precipitacao_total_dia,
                    AVG(h."PRECIPITACAO") AS precipitacao_media_dia,

                    AVG(h."PRESSAO_ATM") AS pressao_atm_dia,
                    SUM(h."RADIACAO") AS radiacao_dia,

                    AVG(h."TEMP_AR") AS temp_ar_dia,
                    MAX(h."TEMP_MAX") AS temp_max_dia,
                    MIN(h."TEMP_MIN") AS temp_min_dia,

                    MAX(h."TEMP_MAX" - h."TEMP_MIN") AS amplitude_t_max_dia,
                    MIN(h."TEMP_MAX" - h."TEMP_MIN") AS amplitude_t_min_dia,
                    AVG(h."TEMP_MAX" - h."TEMP_MIN") AS amplitude_t_media_dia,

                    MAX(h."UMID_MAX") AS umid_max_dia,
                    MIN(h."UMID_MIN") AS umid_min_dia,
                    AVG(h."UMID_AR") AS umid_ar_dia,

                    MAX(h."UMID_MAX" - h."UMID_MIN") AS amplitude_u_max_dia,
                    AVG(h."UMID_MAX" - h."UMID_MIN") AS amplitude_u_media_dia

                FROM {tabela_horaria_ref} h
                {filtro_data}

                GROUP BY
                    h."CODIGO_ESTACAO",
                    DATE_TRUNC('day', h."DATA_HORA")::DATE
            ),

            diario_indicadores AS (
                SELECT
                    d.*,

                    CASE
                        WHEN COALESCE(d.precipitacao_total_dia, 0)
                             >= :limite_chuva_mm
                        THEN 1
                        ELSE 0
                    END AS flag_chuva,

                    CASE
                        WHEN d.temp_max_dia >= :limite_calor_intenso_c
                        THEN 1
                        ELSE 0
                    END AS flag_calor_intenso

                FROM diario d
            ),

            diario_grupos AS (
                SELECT
                    di.*,

                    SUM(
                        CASE
                            WHEN di.flag_chuva = 0 THEN 1
                            ELSE 0
                        END
                    ) OVER (
                        PARTITION BY di.codigo_estacao,
                                     DATE_TRUNC('month', di.dt_dia)
                        ORDER BY di.dt_dia
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS grupo_chuva,

                    SUM(
                        CASE
                            WHEN di.flag_calor_intenso = 0 THEN 1
                            ELSE 0
                        END
                    ) OVER (
                        PARTITION BY di.codigo_estacao,
                                     DATE_TRUNC('month', di.dt_dia)
                        ORDER BY di.dt_dia
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS grupo_calor_intenso

                FROM diario_indicadores di
            ),

            sequencias_chuva AS (
                SELECT
                    codigo_estacao,
                    DATE_TRUNC('month', dt_dia)::DATE AS dt_ref,
                    grupo_chuva,
                    COUNT(*)::INTEGER AS tamanho_sequencia_chuva

                FROM diario_grupos
                WHERE flag_chuva = 1

                GROUP BY
                    codigo_estacao,
                    DATE_TRUNC('month', dt_dia)::DATE,
                    grupo_chuva
            ),

            sequencias_calor AS (
                SELECT
                    codigo_estacao,
                    DATE_TRUNC('month', dt_dia)::DATE AS dt_ref,
                    grupo_calor_intenso,
                    COUNT(*)::INTEGER AS tamanho_sequencia_calor

                FROM diario_grupos
                WHERE flag_calor_intenso = 1

                GROUP BY
                    codigo_estacao,
                    DATE_TRUNC('month', dt_dia)::DATE,
                    grupo_calor_intenso
            ),

            mensal AS (
                SELECT
                    dg.codigo_estacao,
                    DATE_TRUNC('month', dg.dt_dia)::DATE AS dt_ref,

                    (
                        EXTRACT(YEAR FROM dg.dt_dia)::INTEGER * 100
                        + EXTRACT(MONTH FROM dg.dt_dia)::INTEGER
                    ) AS ano_mes,

                    SUM(dg.n_registros_dia)::INTEGER AS n_registros,

                    SUM(dg.precipitacao_total_dia) AS precipitacao_total,
                    AVG(dg.precipitacao_media_dia) AS precipitacao_media,

                    SUM(dg.flag_chuva)::INTEGER AS qtd_dias_chuva,

                    AVG(dg.pressao_atm_dia) AS pressao_atm,
                    SUM(dg.radiacao_dia) AS radiacao,

                    AVG(dg.temp_ar_dia) AS temp_ar,
                    MAX(dg.temp_max_dia) AS temp_max,
                    MIN(dg.temp_min_dia) AS temp_min,

                    MAX(dg.amplitude_t_max_dia) AS amplitude_t_max,
                    MIN(dg.amplitude_t_min_dia) AS amplitude_t_min,
                    AVG(dg.amplitude_t_media_dia) AS amplitude_t_media,

                    SUM(dg.flag_calor_intenso)::INTEGER
                        AS qtd_dias_calor_intenso,

                    MAX(dg.umid_max_dia) AS umid_max,
                    MIN(dg.umid_min_dia) AS umid_min,
                    AVG(dg.umid_ar_dia) AS umid_ar,

                    MAX(dg.amplitude_u_max_dia) AS amplitude_u_max,
                    AVG(dg.amplitude_u_media_dia) AS amplitude_u_media

                FROM diario_grupos dg

                GROUP BY
                    dg.codigo_estacao,
                    DATE_TRUNC('month', dg.dt_dia)::DATE,
                    EXTRACT(YEAR FROM dg.dt_dia)::INTEGER,
                    EXTRACT(MONTH FROM dg.dt_dia)::INTEGER
            ),

            max_sequencias_chuva AS (
                SELECT
                    codigo_estacao,
                    dt_ref,
                    MAX(tamanho_sequencia_chuva)::INTEGER
                        AS max_seq_dias_chuva

                FROM sequencias_chuva

                GROUP BY
                    codigo_estacao,
                    dt_ref
            ),

            max_sequencias_calor AS (
                SELECT
                    codigo_estacao,
                    dt_ref,
                    MAX(tamanho_sequencia_calor)::INTEGER
                        AS max_seq_dias_calor_intenso

                FROM sequencias_calor

                GROUP BY
                    codigo_estacao,
                    dt_ref
            )

            INSERT INTO {tabela_mensal_ref} (
                codigo_estacao,
                dt_ref,
                ano_mes,
                n_registros,

                precipitacao_total,
                precipitacao_media,
                qtd_dias_chuva,

                pressao_atm,
                radiacao,

                temp_ar,
                temp_max,
                temp_min,

                amplitude_t_max,
                amplitude_t_min,
                amplitude_t_media,

                qtd_dias_calor_intenso,
                max_seq_dias_chuva,
                max_seq_dias_calor_intenso,

                umid_max,
                umid_min,
                umid_ar,

                amplitude_u_max,
                amplitude_u_media,

                atualizado_em
            )
            SELECT
                m.codigo_estacao,
                m.dt_ref,
                m.ano_mes,
                m.n_registros,

                m.precipitacao_total,
                m.precipitacao_media,
                m.qtd_dias_chuva,

                m.pressao_atm,
                m.radiacao,

                m.temp_ar,
                m.temp_max,
                m.temp_min,

                m.amplitude_t_max,
                m.amplitude_t_min,
                m.amplitude_t_media,

                m.qtd_dias_calor_intenso,

                COALESCE(sc.max_seq_dias_chuva, 0)
                    AS max_seq_dias_chuva,

                COALESCE(si.max_seq_dias_calor_intenso, 0)
                    AS max_seq_dias_calor_intenso,

                m.umid_max,
                m.umid_min,
                m.umid_ar,

                m.amplitude_u_max,
                m.amplitude_u_media,

                CURRENT_TIMESTAMP AS atualizado_em

            FROM mensal m

            LEFT JOIN max_sequencias_chuva sc
                ON sc.codigo_estacao = m.codigo_estacao
                AND sc.dt_ref = m.dt_ref

            LEFT JOIN max_sequencias_calor si
                ON si.codigo_estacao = m.codigo_estacao
                AND si.dt_ref = m.dt_ref

            ON CONFLICT (codigo_estacao, dt_ref)
            DO UPDATE SET
                ano_mes = EXCLUDED.ano_mes,
                n_registros = EXCLUDED.n_registros,

                precipitacao_total = EXCLUDED.precipitacao_total,
                precipitacao_media = EXCLUDED.precipitacao_media,
                qtd_dias_chuva = EXCLUDED.qtd_dias_chuva,

                pressao_atm = EXCLUDED.pressao_atm,
                radiacao = EXCLUDED.radiacao,

                temp_ar = EXCLUDED.temp_ar,
                temp_max = EXCLUDED.temp_max,
                temp_min = EXCLUDED.temp_min,

                amplitude_t_max = EXCLUDED.amplitude_t_max,
                amplitude_t_min = EXCLUDED.amplitude_t_min,
                amplitude_t_media = EXCLUDED.amplitude_t_media,

                qtd_dias_calor_intenso =
                    EXCLUDED.qtd_dias_calor_intenso,

                max_seq_dias_chuva =
                    EXCLUDED.max_seq_dias_chuva,

                max_seq_dias_calor_intenso =
                    EXCLUDED.max_seq_dias_calor_intenso,

                umid_max = EXCLUDED.umid_max,
                umid_min = EXCLUDED.umid_min,
                umid_ar = EXCLUDED.umid_ar,

                amplitude_u_max = EXCLUDED.amplitude_u_max,
                amplitude_u_media = EXCLUDED.amplitude_u_media,

                atualizado_em = CURRENT_TIMESTAMP;
        """)

        with engine.begin() as conn:
            resultado = conn.execute(
                query_agregacao,
                parametros,
            )

        linhas_processadas = resultado.rowcount

        logger.info(
            (
                "Agregação mensal concluída: %s linhas inseridas ou "
                "atualizadas em %s."
            ),
            f"{linhas_processadas:,}",
            tabela_mensal_ref,
        )

        return linhas_processadas

    finally:
        engine.dispose()