import logging
import re
from datetime import date
from typing import Optional

from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

def validar_identificador(valor: str) -> str:
    """
    Valida identificadores SQL interpolados dinamicamente.

    Permitido: letras, números e underscore, sem iniciar por número.
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


def coluna_ref(coluna: str) -> str:
    """
    Retorna uma referência segura para uma coluna SQL.

    Aspas duplas são usadas para respeitar maiúsculas/minúsculas.
    """
    coluna = validar_identificador(coluna)

    return f'"{coluna}"'


def primeiro_dia_mes(data_referencia: date) -> date:
    """
    Normaliza uma data para o primeiro dia daquele mês.
    """
    return date(
        data_referencia.year,
        data_referencia.month,
        1,
    )

def criar_tabelas_interpolacao(
    engine,
    schema: str,
    tabela_pesos: str,
    tabela_saida: str,
) -> None:
    """
    Cria as tabelas persistidas de pesos IDW e clima interpolado municipal.
    """
    schema = validar_identificador(schema)
    tabela_pesos = validar_identificador(tabela_pesos)
    tabela_saida = validar_identificador(tabela_saida)

    tabela_pesos_ref = tabela_ref(schema, tabela_pesos)
    tabela_saida_ref = tabela_ref(schema, tabela_saida)

    logger.info(
        "Criando ou validando tabelas de interpolação IDW..."
    )

    queries = [
        f'CREATE SCHEMA IF NOT EXISTS "{schema}";',
        f"""
        CREATE TABLE IF NOT EXISTS {tabela_pesos_ref} (
            codigo_municipio TEXT NOT NULL,
            codigo_estacao TEXT NOT NULL,

            distancia_km FLOAT NOT NULL,
            peso_idw FLOAT NOT NULL,
            ordem_proximidade INTEGER NOT NULL,

            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (codigo_municipio, codigo_estacao)
        );
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{tabela_pesos}_municipio"
        ON {tabela_pesos_ref} (codigo_municipio);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{tabela_pesos}_estacao"
        ON {tabela_pesos_ref} (codigo_estacao);
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {tabela_saida_ref} (
            codigo_municipio TEXT NOT NULL,
            dt_ref DATE NOT NULL,
            ano_mes INTEGER NOT NULL,

            n_estacoes INTEGER NOT NULL,
            distancia_min_km FLOAT,
            distancia_med_km FLOAT,
            peso_max FLOAT,

            precipitacao_total FLOAT,
            precipitacao_media FLOAT,
            qtd_dias_chuva FLOAT,

            pressao_atm FLOAT,
            radiacao FLOAT,

            temp_ar FLOAT,
            temp_max FLOAT,
            temp_min FLOAT,

            amplitude_t_max FLOAT,
            amplitude_t_min FLOAT,
            amplitude_t_media FLOAT,

            qtd_dias_calor_intenso FLOAT,
            max_seq_dias_chuva FLOAT,
            max_seq_dias_calor_intenso FLOAT,

            umid_max FLOAT,
            umid_min FLOAT,
            umid_ar FLOAT,

            amplitude_u_max FLOAT,
            amplitude_u_media FLOAT,

            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (codigo_municipio, dt_ref)
        );
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{tabela_saida}_dt_ref"
        ON {tabela_saida_ref} (dt_ref);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{tabela_saida}_ano_mes"
        ON {tabela_saida_ref} (ano_mes);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{tabela_saida}_municipio"
        ON {tabela_saida_ref} (codigo_municipio);
        """,
    ]

    with engine.begin() as conn:
        for query in queries:
            conn.execute(text(query))


# =============================================================================
# Pesos IDW persistidos
# =============================================================================

def criar_ou_atualizar_pesos_idw(
    engine,
    schema: str,
    tabela_municipios: str,
    tabela_estacoes: str,
    tabela_pesos: str,
    coluna_id_municipio: str,
    coluna_lat_municipio: str = "latitude",
    coluna_lon_municipio: str = "longitude",
    coluna_id_estacao: str = "CODIGO_ESTACAO",
    coluna_lat_estacao: str = "LATITUDE",
    coluna_lon_estacao: str = "LONGITUDE",
    k_estacoes: int = 4,
    idw_power: float = 2.0,
) -> int:
    """
    Recalcula os pesos IDW persistidos entre municípios e estações.

    Para cada município, seleciona as K estações geograficamente mais
    próximas e normaliza os pesos de distância inversa.

    Distância calculada pela fórmula Haversine, em quilômetros.
    """
    if k_estacoes < 1:
        raise ValueError("k_estacoes deve ser maior ou igual a 1.")

    if idw_power <= 0:
        raise ValueError("idw_power deve ser maior que zero.")

    schema = validar_identificador(schema)
    tabela_municipios = validar_identificador(tabela_municipios)
    tabela_estacoes = validar_identificador(tabela_estacoes)
    tabela_pesos = validar_identificador(tabela_pesos)

    coluna_id_municipio = validar_identificador(coluna_id_municipio)
    coluna_lat_municipio = validar_identificador(coluna_lat_municipio)
    coluna_lon_municipio = validar_identificador(coluna_lon_municipio)

    coluna_id_estacao = validar_identificador(coluna_id_estacao)
    coluna_lat_estacao = validar_identificador(coluna_lat_estacao)
    coluna_lon_estacao = validar_identificador(coluna_lon_estacao)

    municipios_ref = tabela_ref(schema, tabela_municipios)
    estacoes_ref = tabela_ref(schema, tabela_estacoes)
    pesos_ref = tabela_ref(schema, tabela_pesos)

    municipio_id_ref = coluna_ref(coluna_id_municipio)
    municipio_lat_ref = coluna_ref(coluna_lat_municipio)
    municipio_lon_ref = coluna_ref(coluna_lon_municipio)

    estacao_id_ref = coluna_ref(coluna_id_estacao)
    estacao_lat_ref = coluna_ref(coluna_lat_estacao)
    estacao_lon_ref = coluna_ref(coluna_lon_estacao)

    logger.info(
        "Recalculando pesos IDW: %s estações mais próximas, potência %s...",
        k_estacoes,
        idw_power,
    )

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {pesos_ref};"))

        resultado = conn.execute(
            text(f"""
                WITH municipios_validos AS (
                    SELECT
                        m.{municipio_id_ref}::TEXT AS codigo_municipio,
                        m.{municipio_lat_ref}::FLOAT AS latitude,
                        m.{municipio_lon_ref}::FLOAT AS longitude
                    FROM {municipios_ref} m
                    WHERE m.{municipio_id_ref} IS NOT NULL
                      AND m.{municipio_lat_ref} IS NOT NULL
                      AND m.{municipio_lon_ref} IS NOT NULL
                ),

                estacoes_validas AS (
                    SELECT
                        e.{estacao_id_ref}::TEXT AS codigo_estacao,
                        e.{estacao_lat_ref}::FLOAT AS latitude,
                        e.{estacao_lon_ref}::FLOAT AS longitude
                    FROM {estacoes_ref} e
                    WHERE e.{estacao_id_ref} IS NOT NULL
                      AND e.{estacao_lat_ref} IS NOT NULL
                      AND e.{estacao_lon_ref} IS NOT NULL
                ),

                municipios_estacoes AS (
                    SELECT
                        m.codigo_municipio,
                        e.codigo_estacao,

                        6371.0088 * 2 * ASIN(
                            SQRT(
                                POWER(
                                    SIN(
                                        RADIANS(e.latitude - m.latitude) / 2
                                    ),
                                    2
                                )
                                +
                                COS(RADIANS(m.latitude))
                                * COS(RADIANS(e.latitude))
                                * POWER(
                                    SIN(
                                        RADIANS(e.longitude - m.longitude) / 2
                                    ),
                                    2
                                )
                            )
                        ) AS distancia_km

                    FROM municipios_validos m
                    CROSS JOIN estacoes_validas e
                ),

                estacoes_ordenadas AS (
                    SELECT
                        me.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY me.codigo_municipio
                            ORDER BY me.distancia_km, me.codigo_estacao
                        )::INTEGER AS ordem_proximidade
                    FROM municipios_estacoes me
                ),

                estacoes_selecionadas AS (
                    SELECT
                        eo.*,

                        CASE
                            WHEN eo.distancia_km = 0 THEN 1.0
                            ELSE POWER(
                                1.0 / NULLIF(eo.distancia_km, 0),
                                :idw_power
                            )
                        END AS peso_bruto,

                        MAX(
                            CASE
                                WHEN eo.distancia_km = 0 THEN 1
                                ELSE 0
                            END
                        ) OVER (
                            PARTITION BY eo.codigo_municipio
                        ) AS possui_estacao_mesma_localizacao

                    FROM estacoes_ordenadas eo
                    WHERE eo.ordem_proximidade <= :k_estacoes
                ),

                pesos_normalizados AS (
                    SELECT
                        es.codigo_municipio,
                        es.codigo_estacao,
                        es.distancia_km,
                        es.ordem_proximidade,

                        CASE
                            WHEN es.possui_estacao_mesma_localizacao = 1
                                 AND es.distancia_km = 0
                            THEN 1.0

                            WHEN es.possui_estacao_mesma_localizacao = 1
                            THEN 0.0

                            ELSE
                                es.peso_bruto
                                / NULLIF(
                                    SUM(es.peso_bruto) OVER (
                                        PARTITION BY es.codigo_municipio
                                    ),
                                    0
                                )
                        END AS peso_idw

                    FROM estacoes_selecionadas es
                )

                INSERT INTO {pesos_ref} (
                    codigo_municipio,
                    codigo_estacao,
                    distancia_km,
                    peso_idw,
                    ordem_proximidade,
                    atualizado_em
                )
                SELECT
                    codigo_municipio,
                    codigo_estacao,
                    distancia_km,
                    peso_idw,
                    ordem_proximidade,
                    CURRENT_TIMESTAMP
                FROM pesos_normalizados;
            """),
            {
                "k_estacoes": k_estacoes,
                "idw_power": idw_power,
            },
        )

    linhas_processadas = resultado.rowcount

    logger.info(
        "Pesos IDW persistidos com sucesso: %s relações município-estação.",
        f"{linhas_processadas:,}",
    )

    return linhas_processadas


# =============================================================================
# Interpolação mensal municipal
# =============================================================================

def atualizar_clima_municipal_interpolado(
    db_uri: str,
    schema: str = "modelos",
    tabela_municipios: str = "sz_municipios",
    tabela_estacoes: str = "bz_estacoes",
    tabela_clima_mensal: str = "bz_inmet_clima_mensal",
    tabela_pesos: str = "bz_pesos_idw",
    tabela_saida: str = "bz_municipios_clima_interpolado",
    coluna_id_municipio: str = "codigo_municipio",
    coluna_lat_municipio: str = "latitude",
    coluna_lon_municipio: str = "longitude",
    coluna_id_estacao: str = "CODIGO_ESTACAO",
    coluna_lat_estacao: str = "LATITUDE",
    coluna_lon_estacao: str = "LONGITUDE",
    k_estacoes: int = 4,
    idw_power: float = 2.0,
    recalcular_pesos_idw: bool = False,
    reprocessar_completo: bool = False,
    data_inicio: Optional[date] = None,
) -> int:
    """
    Interpola o clima mensal das estações INMET para cada município usando IDW.

    A tabela de origem deve conter as colunas geradas pelo script
    `inmet_transform_clean.py`:

    - codigo_estacao
    - dt_ref
    - ano_mes
    - precipitacao_total
    - precipitacao_media
    - qtd_dias_chuva
    - pressao_atm
    - radiacao
    - temp_ar
    - temp_max
    - temp_min
    - amplitude_t_max
    - amplitude_t_min
    - amplitude_t_media
    - qtd_dias_calor_intenso
    - max_seq_dias_chuva
    - max_seq_dias_calor_intenso
    - umid_max
    - umid_min
    - umid_ar
    - amplitude_u_max
    - amplitude_u_media
    """
    if not db_uri:
        raise ValueError("db_uri não foi informado.")

    schema = validar_identificador(schema)
    tabela_municipios = validar_identificador(tabela_municipios)
    tabela_estacoes = validar_identificador(tabela_estacoes)
    tabela_clima_mensal = validar_identificador(tabela_clima_mensal)
    tabela_pesos = validar_identificador(tabela_pesos)
    tabela_saida = validar_identificador(tabela_saida)

    engine = create_engine(db_uri)

    tabela_clima_mensal_ref = tabela_ref(schema, tabela_clima_mensal)
    tabela_pesos_ref = tabela_ref(schema, tabela_pesos)
    tabela_saida_ref = tabela_ref(schema, tabela_saida)

    try:
        criar_tabelas_interpolacao(
            engine=engine,
            schema=schema,
            tabela_pesos=tabela_pesos,
            tabela_saida=tabela_saida,
        )

        with engine.connect() as conn:
            possui_clima_mensal = conn.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {tabela_clima_mensal_ref}
                    );
                """)
            ).scalar()

        if not possui_clima_mensal:
            logger.warning(
                "A tabela mensal %s não possui dados. "
                "A interpolação municipal não será executada.",
                tabela_clima_mensal_ref,
            )
            return 0

        with engine.connect() as conn:
            possui_pesos = conn.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {tabela_pesos_ref}
                    );
                """)
            ).scalar()

        if recalcular_pesos_idw or not possui_pesos:
            criar_ou_atualizar_pesos_idw(
                engine=engine,
                schema=schema,
                tabela_municipios=tabela_municipios,
                tabela_estacoes=tabela_estacoes,
                tabela_pesos=tabela_pesos,
                coluna_id_municipio=coluna_id_municipio,
                coluna_lat_municipio=coluna_lat_municipio,
                coluna_lon_municipio=coluna_lon_municipio,
                coluna_id_estacao=coluna_id_estacao,
                coluna_lat_estacao=coluna_lat_estacao,
                coluna_lon_estacao=coluna_lon_estacao,
                k_estacoes=k_estacoes,
                idw_power=idw_power,
            )
        else:
            logger.info(
                "Usando tabela persistida de pesos IDW: %s",
                tabela_pesos_ref,
            )

        if reprocessar_completo:
            logger.info(
                "Reprocessando completamente o clima municipal interpolado..."
            )

            with engine.begin() as conn:
                conn.execute(text(f"TRUNCATE TABLE {tabela_saida_ref};"))

            data_inicio_processamento = None

        elif data_inicio is not None:
            data_inicio_processamento = primeiro_dia_mes(data_inicio)

            logger.info(
                "Interpolando clima municipal desde %s...",
                data_inicio_processamento.isoformat(),
            )

        else:
            with engine.connect() as conn:
                ultimo_mes_processado = conn.execute(
                    text(f"""
                        SELECT MAX(dt_ref)
                        FROM {tabela_saida_ref};
                    """)
                ).scalar()

            data_inicio_processamento = (
                primeiro_dia_mes(ultimo_mes_processado)
                if ultimo_mes_processado is not None
                else None
            )

            if data_inicio_processamento is None:
                logger.info(
                    "Tabela municipal vazia. Interpolando todo o histórico..."
                )
            else:
                logger.info(
                    "Interpolando clima municipal a partir de %s...",
                    data_inicio_processamento.isoformat(),
                )

        filtro_data = ""
        parametros = {}

        if data_inicio_processamento is not None:
            filtro_data = """
                WHERE cm.dt_ref >= :data_inicio
            """

            parametros["data_inicio"] = data_inicio_processamento

            with engine.begin() as conn:
                conn.execute(
                    text(f"""
                        DELETE FROM {tabela_saida_ref}
                        WHERE dt_ref >= :data_inicio;
                    """),
                    {
                        "data_inicio": data_inicio_processamento,
                    },
                )

        # Cada variável é normalizada pela soma dos pesos das estações que
        # TÊM valor naquele mês: os pesos persistidos somam 1 sobre as K
        # estações mais próximas, mas uma delas pode estar inativa ou com o
        # sensor nulo no mês — sem renormalizar, o valor interpolado sairia
        # subestimado (ex.: 1 de 4 estações sem temperatura → ~25 °C vira
        # ~15 °C). Se nenhuma estação tiver valor, o resultado é NULL.
        query_interpolacao = text(f"""
            INSERT INTO {tabela_saida_ref} (
                codigo_municipio,
                dt_ref,
                ano_mes,

                n_estacoes,
                distancia_min_km,
                distancia_med_km,
                peso_max,

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
                p.codigo_municipio,
                cm.dt_ref,
                cm.ano_mes,

                COUNT(*)::INTEGER AS n_estacoes,
                MIN(p.distancia_km) AS distancia_min_km,
                AVG(p.distancia_km) AS distancia_med_km,
                MAX(p.peso_idw) AS peso_max,

                SUM(cm.precipitacao_total * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.precipitacao_total IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS precipitacao_total,

                SUM(cm.precipitacao_media * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.precipitacao_media IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS precipitacao_media,

                SUM(cm.qtd_dias_chuva * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.qtd_dias_chuva IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS qtd_dias_chuva,

                SUM(cm.pressao_atm * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.pressao_atm IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS pressao_atm,

                SUM(cm.radiacao * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.radiacao IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS radiacao,

                SUM(cm.temp_ar * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.temp_ar IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS temp_ar,

                SUM(cm.temp_max * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.temp_max IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS temp_max,

                SUM(cm.temp_min * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.temp_min IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS temp_min,

                SUM(cm.amplitude_t_max * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.amplitude_t_max IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS amplitude_t_max,

                SUM(cm.amplitude_t_min * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.amplitude_t_min IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS amplitude_t_min,

                SUM(cm.amplitude_t_media * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.amplitude_t_media IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS amplitude_t_media,

                SUM(cm.qtd_dias_calor_intenso * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.qtd_dias_calor_intenso IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS qtd_dias_calor_intenso,

                SUM(cm.max_seq_dias_chuva * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.max_seq_dias_chuva IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS max_seq_dias_chuva,

                SUM(cm.max_seq_dias_calor_intenso * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.max_seq_dias_calor_intenso IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS max_seq_dias_calor_intenso,

                SUM(cm.umid_max * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.umid_max IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS umid_max,

                SUM(cm.umid_min * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.umid_min IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS umid_min,

                SUM(cm.umid_ar * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.umid_ar IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS umid_ar,

                SUM(cm.amplitude_u_max * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.amplitude_u_max IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS amplitude_u_max,

                SUM(cm.amplitude_u_media * p.peso_idw)
                    / NULLIF(SUM(CASE WHEN cm.amplitude_u_media IS NOT NULL
                                      THEN p.peso_idw END), 0)
                    AS amplitude_u_media,

                CURRENT_TIMESTAMP AS atualizado_em

            FROM {tabela_pesos_ref} p

            INNER JOIN {tabela_clima_mensal_ref} cm
                ON cm.codigo_estacao::TEXT = p.codigo_estacao

            {filtro_data}

            GROUP BY
                p.codigo_municipio,
                cm.dt_ref,
                cm.ano_mes

            ON CONFLICT (codigo_municipio, dt_ref)
            DO UPDATE SET
                ano_mes = EXCLUDED.ano_mes,

                n_estacoes = EXCLUDED.n_estacoes,
                distancia_min_km = EXCLUDED.distancia_min_km,
                distancia_med_km = EXCLUDED.distancia_med_km,
                peso_max = EXCLUDED.peso_max,

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
                query_interpolacao,
                parametros,
            )

        linhas_processadas = resultado.rowcount

        logger.info(
            "Interpolação IDW concluída: %s linhas municipais inseridas ou atualizadas.",
            f"{linhas_processadas:,}",
        )

        return linhas_processadas

    finally:
        engine.dispose()